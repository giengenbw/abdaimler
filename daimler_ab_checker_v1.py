#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daimler AB 与 Bestellunterlagen 检查工具。

直接运行（同目录包含 BESTELLUNG.pdf 与 AB.pdf）：
    python daimler_ab_checker_v1.py

指定文件：
    python daimler_ab_checker_v1.py "Bestellung.pdf" "AB.pdf" -o Daimler_AB_Check_Report

输出：
    *_ZH.html  中文逐 Code 报告
    *_DE.html  德文逐 Code 报告
    *_Codes.xlsx 逐 Code Excel
    *.json     完整机器可读结果

规则：Bestellung 的所有 Code 必须在 AB 中；"Ohne ..." 缺失允许；AB 多出的 Code
允许；Daimler J-Code/Seriencode 组合通过描述相似度列为 REVIEW，不能静默判定通过。
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
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

# Daimler 主 Code 通常 3-5 位。数字开头 Code（如 03K、58、126）也需保留。
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9]{1,5}$", re.I)
LINE_CODE_RE = re.compile(r"^([A-Z0-9][A-Z0-9]{1,5})\s+(.+)$", re.I)
INLINE_CODE_RE = re.compile(r"(?<![A-Z0-9])([A-Z0-9][A-Z0-9]{1,5})\s+(?=[A-ZÄÖÜ0-9])", re.I)

SECTION_TITLES = {
    "MOTOR", "KUPPLUNG & GETRIEBE", "ACHSEN & AUFHAENGUNG", "ACHSEN & AUFHÄNGUNG",
    "RAEDER & REIFEN", "RÄDER & REIFEN", "RAHMEN & RAHMENANBAUTEILE", "BREMSANLAGE",
    "FAHRERHAUS AUSSEN", "FAHRERHAUS INNEN", "ELEKTRIK / ELEKTRONIK",
    "WEITERE LIEFERUMFAENGE", "WEITERE LIEFERUMFÄNGE", "WEITERE SACHVERHALTE",
    "FAHRZEUGAUSSTATTUNG", "ACHSLASTVERTEILUNG", "SONDERAUSSTATTUNG",
}
HEADER_WORDS = (
    "Vor Übergabe an Kunden", "Kopie erstellen", "Seite ", "Albert Ziegler GmbH",
    "Bestellung von", "DAIMLER TRUCK AG", "Mercedes-Benz", "Auftragsbestätigung",
    "FORTSETZUNG AUF BLATT", "Daimler Truck AG Sitz", "Vorsitzender des Aufsichtsrats",
)
END_WORDS = ("Gesamtpreis Fahrzeug netto", "FAHRZEUGPREIS ZUZUEGLICH", "KAUFPREIS AB WERK")

@dataclass
class CodeItem:
    code: str
    description: str
    page: int
    source: str
    optional_ohne: bool = False

@dataclass
class CodeCheck:
    code: str
    bestellung_description: str
    bestellung_page: int
    status: str
    ab_code: str = ""
    ab_description: str = ""
    ab_page: int = 0
    note_zh: str = ""
    note_de: str = ""


def clean(text: str) -> str:
    text = (text or "").replace("\xa0", " ").replace("­", "")
    return re.sub(r"\s+", " ", text).strip()


def normalize_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def is_probable_code(token: str) -> bool:
    token = normalize_code(token)
    if not CODE_RE.fullmatch(token):
        return False
    # 排除常见正文词和纯页码；2-3位纯数字仅在本地附加项中可作为 Code。
    if token in {"MOTOR", "SEITE", "DATUM", "EUR", "UND", "MIT", "FUER", "VOM", "AB", "WERK", "KOM", "HERR", "IHRE", "WIR", "DEN", "LKW", "GMBH", "HSW", "BNP", "BIC", "IBAN", "BAN"}:
        return False
    if token.isdigit() and len(token) == 1:
        return False
    return any(c.isdigit() for c in token) or (len(token) <= 4 and any(c.isalpha() for c in token))


def extract_text_pages(pdf_file: Path) -> list[str]:
    pages = []
    with pdfplumber.open(str(pdf_file)) as pdf:
        for page in pdf.pages:
            # x_tolerance 对扫描/OCR层中被拆散的字符更稳健。
            text = page.extract_text(x_tolerance=2, y_tolerance=3, layout=False) or ""
            pages.append(text)
    if sum(len(clean(x)) for x in pages) < 100:
        raise RuntimeError(f"{pdf_file.name} 无法提取足够文本，请先进行 OCR。")
    return pages


def split_inline_codes(line: str) -> list[tuple[str, str]]:
    """一行中可能包含多个 Code，按 Code 起点切分。"""
    matches = [m for m in INLINE_CODE_RE.finditer(line) if is_probable_code(m.group(1))]
    result = []
    for i, m in enumerate(matches):
        code = normalize_code(m.group(1))
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        desc = clean(line[m.end():end])
        if desc and len(desc) >= 2:
            result.append((code, desc))
    return result


def extract_codes(pages: list[str], source: str) -> dict[str, CodeItem]:
    """按“每行第一个Token为Code”提取，避免把描述中的大写单词误当Code。"""
    found: dict[str, CodeItem] = {}
    # Daimler Bestellung 的配置在前5页，AB配置在前8页；之后是条款。
    limit = 5 if source == "Bestellung" else 8
    for page_no, text in enumerate(pages[:limit], 1):
        started = page_no > 1
        for raw in text.splitlines():
            line = clean(raw).strip("* ")
            if page_no == 1 and ((source == "Bestellung" and "Fahrgestellausfuehrung" in line) or (source == "AB" and "SONDERAUSSTATTUNG" in line.upper())):
                started = True
                continue
            if not started:
                continue
            if not line or line.upper() in SECTION_TITLES:
                continue
            if any(word.lower() in line.lower() for word in HEADER_WORDS):
                continue
            if any(word.lower() in line.lower() for word in END_WORDS):
                break
            m = LINE_CODE_RE.match(line)
            if not m or not is_probable_code(m.group(1)):
                continue
            code, desc = normalize_code(m.group(1)), clean(m.group(2))
            # 至少一个字母；纯数字仅允许2-3位本地附加项（58、91、126等）。
            if code.isdigit() and not (2 <= len(code) <= 3):
                continue
            if any(x in desc.upper() for x in ("REGISTERGERICHT", "IBAN", "UST-IDNR", "ALBERT-ZIEGLER-STR", "DATUM :")):
                continue
            optional = bool(re.match(r"^(OHNE|ENTFALL)\b", desc, re.I))
            item = CodeItem(code, desc[:600], page_no, source, optional)
            if code not in found or len(desc) > len(found[code].description):
                found[code] = item
    return found


def normalize_description(text: str) -> str:
    text = clean(text).upper()
    replacements = {"UE":"U", "OE":"O", "AE":"A", "ß":"SS", "-":" ", "/":" "}
    for a, b in replacements.items():
        text = text.replace(a, b)
    return re.sub(r"[^A-Z0-9 ]", "", text)


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_description(a), normalize_description(b)).ratio()


def find_j_alternative(item: CodeItem, ab_codes: dict[str, CodeItem], used: set[str]) -> tuple[CodeItem | None, float]:
    """寻找 J-Code/Seriencode 的可能替代项，仅标 REVIEW，不自动当作完全一致。"""
    best = None
    score = 0.0
    for code, candidate in ab_codes.items():
        if code in used:
            continue
        value = similarity(item.description, candidate.description)
        if value > score:
            best, score = candidate, value
    return (best, score) if score >= 0.78 else (None, score)


def compare_codes(best_codes: dict[str, CodeItem], ab_codes: dict[str, CodeItem]) -> tuple[list[CodeCheck], list[CodeItem]]:
    checks: list[CodeCheck] = []
    used_ab: set[str] = set()
    for code, item in best_codes.items():
        if code in ab_codes:
            ab = ab_codes[code]
            used_ab.add(code)
            desc_score = similarity(item.description, ab.description)
            status = "OK" if desc_score >= 0.45 else "REVIEW"
            checks.append(CodeCheck(
                code, item.description, item.page, status, ab.code, ab.description, ab.page,
                "Code存在；描述已匹配。" if status == "OK" else "Code存在，但描述差异较大，请人工核验。",
                "Code vorhanden; Beschreibung abgeglichen." if status == "OK" else "Code vorhanden, aber Beschreibung weicht deutlich ab. Bitte manuell prüfen."
            ))
        elif item.optional_ohne:
            checks.append(CodeCheck(code, item.description, item.page, "IGNORED", note_zh="描述为 Ohne/Entfall，按教程允许AB不出现。", note_de="Beschreibung beginnt mit Ohne/Entfall; gemäß Prüfanweisung darf der Code in der AB fehlen."))
        else:
            alt, score = find_j_alternative(item, ab_codes, used_ab)
            if alt:
                used_ab.add(alt.code)
                checks.append(CodeCheck(code, item.description, item.page, "REVIEW", alt.code, alt.description, alt.page,
                    f"可能是 OCR误识别、Code变更或 Seriencode/J-Code 替代，相似度 {score:.0%}，请人工确认。",
                    f"Mögliche OCR-Abweichung, Code-Änderung oder Seriencode/J-Code-Alternative, Ähnlichkeit {score:.0%}. Bitte manuell prüfen."))
            else:
                checks.append(CodeCheck(code, item.description, item.page, "MISSING", note_zh="Bestellunterlagen 中有此 Code，但 AB 中未找到。", note_de="Dieser Code steht in den Bestellunterlagen, wurde aber in der AB nicht gefunden."))
    extras = [item for code, item in ab_codes.items() if code not in used_ab and code not in best_codes]
    return checks, extras


def first_match(text: str, patterns: Iterable[str]) -> str:
    for pattern in patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            return clean(m.group(1))
    return ""


def extract_key_fields(pages: list[str], source: str) -> dict[str, str]:
    text = "\n".join(pages)
    fields = {
        "project": first_match(text, [r"(A[- ]?\d{7})"]),
        "model": first_match(text, [r"Typ:\s*([^\n]+)", r"MERCEDES\s*-?BENZ\s+([^\n]+?)(?:LKW|BM)"]),
        "wheelbase": first_match(text, [r"Radstand\s*:?\s*(\d+)\s*mm"]),
        "power": first_match(text, [r"Motorleistung\s*:?\s*(\d+)\s*kW", r"MOTOR\s+OM?936.*?(\d+)\s*KW"]),
        "net_price": first_match(text, [r"Gesamtpreis Fahrzeug netto.*?EUR\s*([\d.]+,\d{2})", r"KAUFPREIS AB WERK\s*([\d.]+,\d{2})"]),
        "delivery": first_match(text, [r"UNVERBINDLICHER LIEFERTERMIN\s*:\s*([^\n]+)"]),
        "order_number": first_match(text, [r"AUFTRAGSN(?:U|IIJ|LJ)MMER\s*:\s*([\d ]+)"]),
    }
    return fields


def compare_fields(best: dict[str, str], ab: dict[str, str]) -> list[dict]:
    labels = {"project":"项目号", "model":"车型", "wheelbase":"轴距", "power":"功率", "net_price":"净价", "delivery":"交期", "order_number":"AB订单号"}
    labels_de = {"project":"Projektkennzeichen", "model":"Fahrzeugmodell", "wheelbase":"Radstand", "power":"Motorleistung", "net_price":"Nettopreis", "delivery":"Liefertermin", "order_number":"AB-Auftragsnummer"}
    rows = []
    for key in labels:
        b, a = best.get(key, ""), ab.get(key, "")
        if key == "order_number": status = "INFO"
        elif b and a:
            bn = re.sub(r"[ .]", "", b).casefold(); an = re.sub(r"[ .]", "", a).casefold()
            status = "OK" if (bn == an or bn in an or an in bn) else "REVIEW"
        else: status = "REVIEW"
        rows.append({"key":key, "label_zh":labels[key], "label_de":labels_de[key], "bestellung":b, "ab":a, "status":status})
    return rows


def write_outputs(base: Path, payload: dict) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    excel_rows = []
    for x in payload["code_checks"]:
        excel_rows.append({"Bestellung Code":x["code"], "Bestellung Description":x["bestellung_description"], "Bestellung Page":x["bestellung_page"], "Status":x["status"], "AB Code":x["ab_code"], "AB Description":x["ab_description"], "AB Page":x["ab_page"], "说明":x["note_zh"], "Hinweis":x["note_de"]})
    for x in payload["extra_in_ab"]:
        excel_rows.append({"Bestellung Code":"", "Bestellung Description":"", "Bestellung Page":"", "Status":"EXTRA", "AB Code":x["code"], "AB Description":x["description"], "AB Page":x["page"], "说明":"AB额外Code，按规则允许。", "Hinweis":"Zusätzlicher Code in der AB; gemäß Regel zulässig."})
    df = pd.DataFrame(excel_rows)
    xlsx = Path(str(base) + "_Codes.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Code Check")
        pd.DataFrame(payload["field_checks"]).to_excel(writer, index=False, sheet_name="Key Fields")
        ws = writer.book["Code Check"]
        ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
        widths = {"A":18,"B":55,"C":16,"D":14,"E":14,"F":55,"G":12,"H":48,"I":55}
        for col, width in widths.items(): ws.column_dimensions[col].width = width

    css = """<style>body{font-family:Arial,'Microsoft YaHei',sans-serif;margin:26px;color:#222}table{border-collapse:collapse;width:100%;margin:15px 0 25px}th,td{border:1px solid #bbb;padding:7px;vertical-align:top}th{background:#e9eef5;position:sticky;top:0}.OK{color:#087830;font-weight:bold}.MISSING{color:#b00020;font-weight:bold}.REVIEW{color:#9a6700;font-weight:bold}.IGNORED,.EXTRA,.INFO{color:#555;font-weight:bold}.summary{padding:12px;background:#f6f8fa;border:1px solid #ccc}.code{font-family:Consolas,monospace;font-weight:bold;white-space:nowrap}.small{font-size:12px;color:#555}</style>"""

    def make_html(lang: str) -> str:
        zh = lang == "zh"
        status_name = {"OK":"OK", "MISSING":"缺失" if zh else "FEHLT", "REVIEW":"复核" if zh else "PRÜFEN", "IGNORED":"忽略" if zh else "IGNORIERT", "EXTRA":"额外" if zh else "ZUSÄTZLICH", "INFO":"信息" if zh else "INFO"}
        field_rows = "".join(f"<tr><td>{html.escape(x['label_zh' if zh else 'label_de'])}</td><td class='{x['status']}'>{status_name.get(x['status'],x['status'])}</td><td>{html.escape(x['bestellung'])}</td><td>{html.escape(x['ab'])}</td></tr>" for x in payload["field_checks"])
        code_rows = "".join(f"<tr><td class='code'>{html.escape(x['code'])}</td><td>{html.escape(x['bestellung_description'])}</td><td>{x['bestellung_page']}</td><td class='{x['status']}'>{status_name[x['status']]}</td><td class='code'>{html.escape(x['ab_code'])}</td><td>{html.escape(x['ab_description'])}</td><td>{x['ab_page'] or ''}</td><td>{html.escape(x['note_zh' if zh else 'note_de'])}</td></tr>" for x in payload["code_checks"])
        extra_rows = "".join(f"<tr><td class='code'>{html.escape(x['code'])}</td><td>{html.escape(x['description'])}</td><td>{x['page']}</td></tr>" for x in payload["extra_in_ab"]) or ("<tr><td colspan='3'>无</td></tr>" if zh else "<tr><td colspan='3'>Keine</td></tr>")
        title = "Daimler AB 自动检查报告" if zh else "Automatischer Daimler AB-Prüfbericht"
        conclusion = payload["overall_zh"] if zh else payload["overall_de"]
        labels = (["关键字段检查","检查项","状态","Bestellunterlagen","AB","每一个 Code 的检查结果","Bestellung Code","描述","页码","状态","AB Code","AB描述","AB页码","说明","AB额外 Codes（允许）"] if zh else ["Prüfung der Schlüsselfelder","Prüfpunkt","Status","Bestellunterlagen","AB","Prüfergebnis für jeden einzelnen Code","Bestellung Code","Beschreibung","Seite","Status","AB Code","AB-Beschreibung","AB-Seite","Hinweis","Zusätzliche Codes in der AB (zulässig)"])
        return f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><title>{title}</title>{css}</head><body><h1>{title}</h1><div class='summary'><b>{'结论' if zh else 'Ergebnis'}:</b> {html.escape(conclusion)}<br><b>Bestellunterlagen:</b> {html.escape(payload['bestellung_file'])}<br><b>AB:</b> {html.escape(payload['ab_file'])}<br><b>{'Code统计' if zh else 'Code-Statistik'}:</b> OK {payload['counts']['OK']} | MISSING {payload['counts']['MISSING']} | REVIEW {payload['counts']['REVIEW']} | IGNORED {payload['counts']['IGNORED']} | EXTRA {payload['counts']['EXTRA']}</div><h2>{labels[0]}</h2><table><tr><th>{labels[1]}</th><th>{labels[2]}</th><th>{labels[3]}</th><th>{labels[4]}</th></tr>{field_rows}</table><h2>{labels[5]}</h2><table><tr><th>{labels[6]}</th><th>{labels[7]}</th><th>{labels[8]}</th><th>{labels[9]}</th><th>{labels[10]}</th><th>{labels[11]}</th><th>{labels[12]}</th><th>{labels[13]}</th></tr>{code_rows}</table><h2>{labels[14]}</h2><table><tr><th>Code</th><th>{labels[7]}</th><th>{labels[8]}</th></tr>{extra_rows}</table><p class='small'>{'自动提取可能受OCR和PDF排版影响。MISSING和REVIEW必须人工复核。' if zh else 'Die automatische Extraktion kann durch OCR und PDF-Layout beeinflusst werden. FEHLT und PRÜFEN müssen manuell kontrolliert werden.'}</p></body></html>"

    Path(str(base) + "_ZH.html").write_text(make_html("zh"), encoding="utf-8")
    Path(str(base) + "_DE.html").write_text(make_html("de"), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Daimler AB 与 Bestellunterlagen 逐 Code 检查")
    p.add_argument("bestellung", nargs="?", type=Path, default=Path("BESTELLUNG.pdf"))
    p.add_argument("ab", nargs="?", type=Path, default=Path("AB.pdf"))
    p.add_argument("-o", "--output", type=Path, default=Path("Daimler_AB_Check_Report"))
    args = p.parse_args()
    for f in (args.bestellung, args.ab):
        if not f.is_file(): p.error(f"文件不存在: {f}")

    best_pages = extract_text_pages(args.bestellung); ab_pages = extract_text_pages(args.ab)
    best_codes = extract_codes(best_pages, "Bestellung"); ab_codes = extract_codes(ab_pages, "AB")
    checks, extras = compare_codes(best_codes, ab_codes)
    field_checks = compare_fields(extract_key_fields(best_pages, "Bestellung"), extract_key_fields(ab_pages, "AB"))
    counts = {s:sum(1 for x in checks if x.status == s) for s in ("OK","MISSING","REVIEW","IGNORED")}; counts["EXTRA"] = len(extras)
    bad = counts["MISSING"] > 0
    review = counts["REVIEW"] > 0 or any(x["status"] == "REVIEW" for x in field_checks)
    payload = {
        "bestellung_file":str(args.bestellung), "ab_file":str(args.ab),
        "overall_zh":"不正确，存在缺失Code" if bad else ("需人工复核" if review else "Code检查通过"),
        "overall_de":"Nicht korrekt, Codes fehlen" if bad else ("Manuelle Prüfung erforderlich" if review else "Code-Prüfung bestanden"),
        "counts":counts, "field_checks":field_checks,
        "code_checks":[asdict(x) for x in checks], "extra_in_ab":[asdict(x) for x in extras],
    }
    write_outputs(args.output, payload)
    print(json.dumps({"结果":payload["overall_zh"], "Bestellung Codes":len(best_codes), "AB Codes":len(ab_codes), "统计":counts, "中文报告":str(args.output)+"_ZH.html", "德文报告":str(args.output)+"_DE.html", "Excel":str(args.output)+"_Codes.xlsx"}, ensure_ascii=False, indent=2))
    return 2 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
