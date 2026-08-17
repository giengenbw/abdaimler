#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daimler AB 与 Bestellunterlagen 检查工具 v3。

改进：
1. 使用 PDF 单词坐标重新组行，不再依赖 page.extract_text() 的换行。
2. 第一页从“Fahrzeugausstattung/FAHRGESTELLAUSFUEHRUNG”起提取 V1D、V1W、C2A。
3. 车型、轴距、功率、价格、交期、订单号使用更稳健的字段规则。
4. 保留 OCR 容错，但 J-Code/Seriencode 替代仍只标 REVIEW。
"""
from __future__ import annotations

import argparse, difflib, html, json, re, sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    import pdfplumber
except ImportError:
    raise SystemExit("缺少 pdfplumber，请运行: python -m pip install pdfplumber")
try:
    import pandas as pd
except ImportError:
    raise SystemExit("缺少 pandas/openpyxl，请运行: python -m pip install pandas openpyxl")

CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9]{1,5}$", re.I)
LINE_CODE_RE = re.compile(r"^([A-Z0-9][A-Z0-9]{1,5})\s+(.+)$", re.I)
SECTION_TITLES = {
    "FAHRGESTELLAUSFUEHRUNG", "FAHRZEUGAUSSTATTUNG", "ACHSLASTVERTEILUNG", "MOTOR",
    "KUPPLUNG & GETRIEBE", "ACHSEN & AUFHAENGUNG", "ACHSEN & AUFHÄNGUNG",
    "RAEDER & REIFEN", "RÄDER & REIFEN", "RAHMEN & RAHMENANBAUTEILE", "BREMSANLAGE",
    "FAHRERHAUS AUSSEN", "FAHRERHAUS INNEN", "ELEKTRIK / ELEKTRONIK",
    "WEITERE LIEFERUMFAENGE", "WEITERE LIEFERUMFÄNGE", "WEITERE SACHVERHALTE", "SONDERAUSSTATTUNG",
}
HEADER_WORDS = (
    "Vor Übergabe an Kunden", "Kopie erstellen", "Seite ", "Albert Ziegler GmbH",
    "Bestellung von", "DAIMLER TRUCK AG", "Mercedes-Benz", "Auftragsbestätigung",
    "FORTSETZUNG AUF BLATT", "Daimler Truck AG Sitz", "Vorsitzender des Aufsichtsrats",
)
END_WORDS = ("Gesamtpreis Fahrzeug netto", "FAHRZEUGPREIS INKLUSIVE", "KAUFPREIS AB WERK")
STOP_CODES = {"MOTOR","SEITE","DATUM","EUR","UND","MIT","FUER","VOM","WERK","KOM","HERR","IHRE","WIR","DEN","LKW","GMBH","HSW","BNP","BIC","IBAN","BAN","TYP","MB","PS","NM","MM","AG","SITZ","JOHN"}

@dataclass
class CodeItem:
    code: str; description: str; page: int; source: str; optional_ohne: bool = False
@dataclass
class CodeCheck:
    code: str; bestellung_description: str; bestellung_page: int; status: str
    ab_code: str = ""; ab_description: str = ""; ab_page: int = 0; note_zh: str = ""; note_de: str = ""

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ").replace("­", "")).strip()
def normalize_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", code.upper())
def is_probable_code(token: str, *, at_line_start: bool = False) -> bool:
    """判断是否可能为 Daimler Code。

    行首采用 v1 的宽松规则，因此 K0F、KOF、ZSX、JFFS 等均可保留。
    行内切分采用较严格规则，避免把 MOTOR、MIT、WERK 等正文词误认成 Code。
    """
    token = normalize_code(token)
    if not CODE_RE.fullmatch(token) or token in STOP_CODES:
        return False
    if token.isdigit():
        # 纯数字 Code 仅允许位于视觉行首，避免把容量 130、功率 220 等识别成 Code。
        return at_line_start and 2 <= len(token) <= 3
    if any(c.isdigit() for c in token):
        return True
    if at_line_start:
        return len(token) <= 5 and any(c.isalpha() for c in token)
    return bool(re.fullmatch(r"J[A-Z]{2,4}", token)) or token in {"ZSX"}

def code_ocr_variants(code: str) -> set[str]:
    """生成少量常见 OCR 变体，仅用于寻找 REVIEW 候选，不直接判定 OK。"""
    code = normalize_code(code)
    groups = ({"0", "O", "Q"}, {"1", "I", "L"}, {"5", "S"}, {"8", "B"})
    variants = {code}
    for i, ch in enumerate(code):
        for group in groups:
            if ch in group:
                variants.update(code[:i] + repl + code[i + 1:] for repl in group)
    return variants

def codes_ocr_equivalent(a: str, b: str) -> bool:
    a, b = normalize_code(a), normalize_code(b)
    return len(a) == len(b) and b in code_ocr_variants(a)

def page_lines(page) -> list[str]:
    """按 y 坐标组行。解决 extract_text 将第一页压成一整行的问题。"""
    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False) or []
    rows: list[dict] = []
    for w in sorted(words, key=lambda x: (x["top"], x["x0"])):
        cy = (w["top"] + w["bottom"]) / 2
        row = next((r for r in reversed(rows[-5:]) if abs(r["y"] - cy) <= 3.2), None)
        if row is None:
            row = {"y": cy, "words": []}; rows.append(row)
        row["words"].append(w); row["y"] = sum((x["top"]+x["bottom"])/2 for x in row["words"]) / len(row["words"])
    return [clean(" ".join(x["text"] for x in sorted(r["words"], key=lambda z: z["x0"]))) for r in rows]

def extract_pdf(pdf_file: Path) -> tuple[list[str], list[list[str]]]:
    texts, lines = [], []
    with pdfplumber.open(str(pdf_file)) as pdf:
        for page in pdf.pages:
            ls = page_lines(page)
            lines.append(ls); texts.append("\n".join(ls))
    if sum(len(clean(x)) for x in texts) < 100:
        raise RuntimeError(f"{pdf_file.name} 无法提取足够文本，请先进行 OCR。")
    return texts, lines

def trim_line(line: str, source: str, page_no: int) -> str:
    """去掉同一视觉行中的页眉/页脚前缀，并保留其后的首个配置 Code。"""
    if page_no == 1:
        anchors = ["Fahrzeugausstattung:", "FAHRGESTELLAUSFUEHRUNG", "SONDERAUSSTATTUNG:"]
        positions = [line.upper().find(a.upper()) for a in anchors if line.upper().find(a.upper()) >= 0]
        if positions:
            p = min(positions)
            segment = line[p:]
            # 标题后可能先有说明，再出现 V1D；从第一个可信 Code 开始。
            m = re.search(r"(?<![A-Z0-9])([A-Z0-9]{2,6})\s+", segment, re.I)
            while m and not is_probable_code(m.group(1)):
                nxt = re.search(r"(?<![A-Z0-9])([A-Z0-9]{2,6})\s+", segment[m.end():], re.I)
                if not nxt: m = None; break
                off = m.end(); m = re.Match if False else nxt
                # easier: handled below by token scan
                break
            tokens = list(re.finditer(r"(?<![A-Z0-9])([A-Z0-9]{2,6})(?=\s)", segment, re.I))
            valid = next((x for x in tokens if is_probable_code(x.group(1))), None)
            if valid: return segment[valid.start():]
    return line

def extract_codes(page_texts: list[str], page_rows: list[list[str]], source: str) -> dict[str, CodeItem]:
    """坐标组行后提取 Code。

    规则：
    1. 每个视觉行的第一个 Token 使用 v1 宽松规则。
    2. OCR 将多个配置压到一行时，再用严格规则识别后续 Code。
    3. 第一页从 Fahrzeugausstattung/FAHRGESTELLAUSFUEHRUNG 后开始。
    """
    found: dict[str, CodeItem] = {}
    limit = 5 if source == "Bestellung" else 8
    for page_no, rows in enumerate(page_rows[:limit], 1):
        started = page_no > 1
        for raw in rows:
            original = clean(raw).strip("* ")
            if not original:
                continue
            upper = original.upper()
            if page_no == 1 and any(a in upper for a in (
                "FAHRZEUGAUSSTATTUNG", "FAHRGESTELLAUSFUEHRUNG", "SONDERAUSSTATTUNG"
            )):
                started = True
                original = trim_line(original, source, page_no)
                upper = original.upper()
            if not started or not original:
                continue
            if any(x.lower() in original.lower() for x in END_WORDS):
                break
            if original.upper() in SECTION_TITLES:
                continue
            if any(x.lower() in original.lower() for x in HEADER_WORDS) and not any(
                a in upper for a in ("FAHRZEUGAUSSTATTUNG", "FAHRGESTELLAUSFUEHRUNG", "SONDERAUSSTATTUNG")
            ):
                continue

            starts = []
            first = re.match(r"^([A-Z0-9]{2,6})\s+", original, re.I)
            if first and is_probable_code(first.group(1), at_line_start=True):
                starts.append(first)

            # 对同一视觉行后续位置使用严格规则，避免普通描述单词造成大量假 Code。
            for m in re.finditer(r"(?<![A-Z0-9])([A-Z0-9]{2,6})\s+(?=[A-ZÄÖÜ0-9])", original, re.I):
                if first and m.start() == first.start():
                    continue
                if is_probable_code(m.group(1), at_line_start=False):
                    starts.append(m)
            starts.sort(key=lambda m: m.start())
            if not starts:
                continue

            for i, m in enumerate(starts):
                code = normalize_code(m.group(1))
                end_pos = starts[i + 1].start() if i + 1 < len(starts) else len(original)
                desc = clean(original[m.end():end_pos])
                if len(desc) < 2:
                    continue
                if any(x in desc.upper() for x in (
                    "REGISTERGERICHT", "IBAN", "UST-IDNR", "ALBERT-ZIEGLER-STR", "DATUM :"
                )):
                    continue
                optional = bool(re.match(r"^(OHNE|ENTFALL)\b", desc, re.I))
                item = CodeItem(code, desc[:600], page_no, source, optional)
                if code not in found or len(desc) > len(found[code].description):
                    found[code] = item
    return found

def normalize_description(text: str) -> str:
    t = clean(text).upper().replace("ß", "SS")
    for a,b in {"UE":"U","OE":"O","AE":"A","-":" ","/":" "}.items(): t=t.replace(a,b)
    return re.sub(r"[^A-Z0-9 ]", "", t)
def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_description(a), normalize_description(b)).ratio()
def find_j_alternative(item, ab_codes, used):
    """先找 OCR 等价 Code，再找高描述相似度候选，结果始终为 REVIEW。"""
    best = None
    score = 0.0
    for code, candidate in ab_codes.items():
        if code in used:
            continue
        desc_score = similarity(item.description, candidate.description)
        ocr_bonus = 0.25 if codes_ocr_equivalent(item.code, code) else 0.0
        value = min(1.0, desc_score + ocr_bonus)
        if value > score:
            best, score = candidate, value
    return (best, score) if score >= 0.78 else (None, score)

def compare_codes(best_codes, ab_codes):
    checks=[]; used=set()
    for code,item in best_codes.items():
        if code in ab_codes:
            ab=ab_codes[code]; used.add(code); s=similarity(item.description,ab.description); status="OK" if s>=0.45 else "REVIEW"
            checks.append(CodeCheck(code,item.description,item.page,status,ab.code,ab.description,ab.page,
                "Code存在；描述已匹配。" if status=="OK" else "Code存在，但描述差异较大，请人工核验。",
                "Code vorhanden; Beschreibung abgeglichen." if status=="OK" else "Code vorhanden, aber Beschreibung weicht deutlich ab. Bitte manuell prüfen."))
        elif item.optional_ohne:
            checks.append(CodeCheck(code,item.description,item.page,"IGNORED",note_zh="描述为 Ohne/Entfall，允许AB不出现。",note_de="Ohne/Entfall; der Code darf in der AB fehlen."))
        else:
            alt,score=find_j_alternative(item,ab_codes,used)
            if alt:
                used.add(alt.code); checks.append(CodeCheck(code,item.description,item.page,"REVIEW",alt.code,alt.description,alt.page,f"可能为OCR/Code变更/J-Code替代，相似度 {score:.0%}，请人工确认。",f"Mögliche OCR-/Code-Abweichung oder J-Code-Alternative, Ähnlichkeit {score:.0%}."))
            else: checks.append(CodeCheck(code,item.description,item.page,"MISSING",note_zh="Bestellunterlagen 中有此 Code，但 AB 中未找到。",note_de="Code in den Bestellunterlagen vorhanden, in der AB nicht gefunden."))
    return checks,[x for c,x in ab_codes.items() if c not in used and c not in best_codes]

def first_match(text: str, patterns: Iterable[str]) -> str:
    for p in patterns:
        m=re.search(p,text,re.I|re.S)
        if m: return clean(m.group(1))
    return ""
def extract_key_fields(pages: list[str], source: str) -> dict[str,str]:
    text="\n".join(pages); flat=clean(text)
    model_patterns = ([r"/\s*#(?:Atego Neu Verteiler\s+)?([^\n]+?)\s+-\s+F1X", r"Typ\s*:\s*([^\n]+?)(?=\s+Radstand\s*:)"] if source=="Bestellung" else [r"\b1\s+MERCEDES\s*-?BENZ\s+(.+?)(?=\s+LKW\s+FEUERWEHRFAHRGESTELL)", r"MERCEDES\s*-?BENZ\s+(.+?)(?=\s+BM\s+\d{6,})"])
    price_patterns = [r"Gesamtpreis Fahrzeug netto.*?EUR\s*([\d.]+,\d{2})"] if source=="Bestellung" else [r"FAHRZEUGPREIS INKLUSIVE SONDERNACHLAESSE\s*([\d. ]+,\d{2})"]
    return {
      "project":first_match(text,[r"(?<![A-Z0-9])(A[- ]?\d{7})(?!\d)"]),
      "model":first_match(text,model_patterns),
      "wheelbase":first_match(flat,[r"(?:Radstand|Padstand)\s*:?\s*(\d+)\s*mm"]),
      "power":first_match(flat,[r"Motorleistung\s*:?\s*(\d+)\s*kW",r"MOTOR\s+[0O]M?936.*?\b(\d+)\s*KW"]),
      "net_price":first_match(flat,price_patterns).replace(" ", ""),
      "delivery":first_match(flat,[r"(?:UNVERBINDLICHER|UI.JVERBINDLICHER|UNVERBINDL\w*)\s+LIEFERTERMIN\s*:\s*(.+?)(?=\s+(?:VERSANDART|LACKIERUNG|FAHRZEUGAUSSTATTUNG|$))"]),
      "order_number":first_match(flat,[r"AUFTRAGS(?:NUMMER|NUNMER|NDNMER|NtJMMER)\s*:\s*([\d ]{8,})",r"Auftrags-Nummer\s+(\d{8,})"]),
    }
def compare_fields(best,ab):
    zh={"project":"项目号","model":"车型","wheelbase":"轴距","power":"功率","net_price":"净价","delivery":"交期","order_number":"AB订单号"}; de={"project":"Projektkennzeichen","model":"Fahrzeugmodell","wheelbase":"Radstand","power":"Motorleistung","net_price":"Nettopreis","delivery":"Liefertermin","order_number":"AB-Auftragsnummer"}
    rows=[]
    for k in zh:
        b,a=best.get(k,""),ab.get(k,"")
        status="INFO" if k=="order_number" else ("OK" if b and a and (re.sub(r"[ .]","",b).casefold()==re.sub(r"[ .]","",a).casefold() or re.sub(r"[ .]","",b).casefold() in re.sub(r"[ .]","",a).casefold() or re.sub(r"[ .]","",a).casefold() in re.sub(r"[ .]","",b).casefold()) else "REVIEW")
        rows.append({"key":k,"label_zh":zh[k],"label_de":de[k],"bestellung":b,"ab":a,"status":status})
    return rows

def write_outputs(base: Path,payload: dict):
    base.parent.mkdir(parents=True,exist_ok=True); base.with_suffix(".json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    rows=[{"Bestellung Code":x["code"],"Bestellung Description":x["bestellung_description"],"Bestellung Page":x["bestellung_page"],"Status":x["status"],"AB Code":x["ab_code"],"AB Description":x["ab_description"],"AB Page":x["ab_page"],"说明":x["note_zh"],"Hinweis":x["note_de"]} for x in payload["code_checks"]]
    rows += [{"Bestellung Code":"","Bestellung Description":"","Bestellung Page":"","Status":"EXTRA","AB Code":x["code"],"AB Description":x["description"],"AB Page":x["page"],"说明":"AB额外Code，允许。","Hinweis":"Zusätzlicher Code in der AB; zulässig."} for x in payload["extra_in_ab"]]
    xlsx_path = Path(str(base) + "_Codes.xlsx")
    try:
        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
            pd.DataFrame(rows).to_excel(w, index=False, sheet_name="Code Check")
            pd.DataFrame(payload["field_checks"]).to_excel(w, index=False, sheet_name="Key Fields")
            ws = w.book["Code Check"]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for c, v in {"A":18,"B":55,"C":16,"D":14,"E":14,"F":55,"G":12,"H":48,"I":55}.items():
                ws.column_dimensions[c].width = v
    except PermissionError as exc:
        raise RuntimeError(
            f"无法写入 {xlsx_path}。请关闭正在打开的 Excel 文件，或使用 -o 指定新的输出名称。"
        ) from exc
    css="<style>body{font-family:Arial,'Microsoft YaHei',sans-serif;margin:26px;color:#222}table{border-collapse:collapse;width:100%;margin:15px 0 25px}th,td{border:1px solid #bbb;padding:7px;vertical-align:top}th{background:#e9eef5}.OK{color:#087830;font-weight:bold}.MISSING{color:#b00020;font-weight:bold}.REVIEW{color:#9a6700;font-weight:bold}.IGNORED,.EXTRA,.INFO{color:#555;font-weight:bold}.summary{padding:12px;background:#f6f8fa;border:1px solid #ccc}.code{font-family:Consolas,monospace;font-weight:bold}</style>"
    def report(zh):
        sn={"OK":"OK","MISSING":"缺失" if zh else "FEHLT","REVIEW":"复核" if zh else "PRÜFEN","IGNORED":"忽略" if zh else "IGNORIERT","INFO":"信息" if zh else "INFO"}; title="Daimler AB 自动检查报告" if zh else "Automatischer Daimler AB-Prüfbericht"
        fr="".join(f"<tr><td>{html.escape(x['label_zh' if zh else 'label_de'])}</td><td class='{x['status']}'>{sn[x['status']]}</td><td>{html.escape(x['bestellung'])}</td><td>{html.escape(x['ab'])}</td></tr>" for x in payload["field_checks"])
        cr="".join(f"<tr><td class='code'>{html.escape(x['code'])}</td><td>{html.escape(x['bestellung_description'])}</td><td>{x['bestellung_page']}</td><td class='{x['status']}'>{sn[x['status']]}</td><td>{html.escape(x['ab_code'])}</td><td>{html.escape(x['ab_description'])}</td><td>{x['ab_page'] or ''}</td><td>{html.escape(x['note_zh' if zh else 'note_de'])}</td></tr>" for x in payload["code_checks"])
        return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>{css}</head><body><h1>{title}</h1><div class='summary'><b>{'结论' if zh else 'Ergebnis'}:</b> {html.escape(payload['overall_zh' if zh else 'overall_de'])}<br>OK {payload['counts']['OK']} | MISSING {payload['counts']['MISSING']} | REVIEW {payload['counts']['REVIEW']} | IGNORED {payload['counts']['IGNORED']} | EXTRA {payload['counts']['EXTRA']}</div><h2>{'关键字段' if zh else 'Schlüsselfelder'}</h2><table><tr><th>Field</th><th>Status</th><th>Bestellung</th><th>AB</th></tr>{fr}</table><h2>Codes</h2><table><tr><th>Code</th><th>Description</th><th>Page</th><th>Status</th><th>AB Code</th><th>AB Description</th><th>Page</th><th>Note</th></tr>{cr}</table></body></html>"
    Path(str(base)+"_ZH.html").write_text(report(True),encoding="utf-8"); Path(str(base)+"_DE.html").write_text(report(False),encoding="utf-8")

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("bestellung",nargs="?",type=Path,default=Path("BESTELLUNG.pdf")); p.add_argument("ab",nargs="?",type=Path,default=Path("AB.pdf")); p.add_argument("-o","--output",type=Path,default=Path("Daimler_AB_Check_Report")); a=p.parse_args()
    for f in (a.bestellung,a.ab):
        if not f.is_file(): p.error(f"文件不存在: {f}")
    bt,bl=extract_pdf(a.bestellung); at,al=extract_pdf(a.ab); bc=extract_codes(bt,bl,"Bestellung"); ac=extract_codes(at,al,"AB"); checks,extras=compare_codes(bc,ac); fields=compare_fields(extract_key_fields(bt,"Bestellung"),extract_key_fields(at,"AB")); counts={s:sum(x.status==s for x in checks) for s in ("OK","MISSING","REVIEW","IGNORED")}; counts["EXTRA"]=len(extras); bad=counts["MISSING"]>0; review=counts["REVIEW"]>0 or any(x["status"]=="REVIEW" for x in fields)
    payload={"bestellung_file":str(a.bestellung),"ab_file":str(a.ab),"overall_zh":"不正确，存在缺失Code" if bad else ("需人工复核" if review else "Code检查通过"),"overall_de":"Nicht korrekt, Codes fehlen" if bad else ("Manuelle Prüfung erforderlich" if review else "Code-Prüfung bestanden"),"counts":counts,"field_checks":fields,"code_checks":[asdict(x) for x in checks],"extra_in_ab":[asdict(x) for x in extras]}; write_outputs(a.output,payload)
    print(json.dumps({"结果":payload["overall_zh"],"Bestellung Codes":len(bc),"AB Codes":len(ac),"第一页Bestellung Codes":[c for c,x in bc.items() if x.page==1],"第一页AB Codes":[c for c,x in ac.items() if x.page==1],"关键字段":fields,"统计":counts},ensure_ascii=False,indent=2)); return 2 if bad else 0
if __name__=="__main__": sys.exit(main())
