# Daimler AB 自动检查工具 / Werkzeug zur automatisierten Prüfung von Daimler-Auftragsbestätigungen

本项目用于在本地比较 Daimler 的 **Bestellunterlagen（订购资料）** 与 **Auftragsbestätigung，简称 AB（订单确认书）**，辅助采购人员检查订单编号、车辆配置、价格、技术参数、交期、付款条件以及送货信息。

Dieses Projekt dient dem lokalen Vergleich von Daimler-**Bestellunterlagen** mit der **Auftragsbestätigung (AB)**. Es unterstützt den Einkauf bei der Prüfung von Bestellnummern, Fahrzeugkonfigurationen, Preisen, technischen Daten, Lieferterminen, Zahlungsbedingungen und Lieferangaben.

> **重要：公司隐私与数据保护 / Wichtig: Vertraulichkeit und Datenschutz im Unternehmen**
>
> 订单、报价、车辆配置、采购价格、客户编号、供应商信息、联系人和送货地址可能属于公司机密或个人信息。请仅在公司授权的设备和目录中运行本工具。不要将真实 PDF、Excel、检查报告、终端截图或处理结果提交到 GitHub，也不要上传至公共云盘、在线 OCR、在线 PDF 转换网站或未经公司批准的 AI 服务。
>
> Bestellungen, Angebote, Fahrzeugkonfigurationen, Einkaufspreise, Kundennummern, Lieferanteninformationen, Kontaktdaten und Lieferadressen können vertrauliche Unternehmensinformationen oder personenbezogene Daten enthalten. Verwenden Sie dieses Werkzeug ausschließlich auf vom Unternehmen freigegebenen Geräten und in freigegebenen Verzeichnissen. Laden Sie keine echten PDF- oder Excel-Dateien, Prüfberichte, Terminal-Screenshots oder Verarbeitungsergebnisse auf GitHub, öffentliche Cloud-Speicher, Online-OCR-Dienste, Online-PDF-Konverter oder nicht vom Unternehmen freigegebene KI-Dienste hoch.

## 功能概览 / Funktionsübersicht

根据项目中实际使用的脚本，工具可用于以下辅助检查：

Abhängig von den tatsächlich im Projekt verwendeten Skripten kann das Werkzeug folgende unterstützende Prüfungen durchführen:

- 读取 Daimler Bestellunterlagen 和 AB 文件。 / Einlesen von Daimler-Bestellunterlagen und AB-Dateien.
- 提取订单号、报价号或客户订单号。 / Extraktion von Bestellnummern, Angebotsnummern oder Kundenbestellnummern.
- 比较车辆配置 Code。 / Vergleich der Fahrzeugausstattungscodes.
- 检查净价和主要技术参数。 / Prüfung von Nettopreisen und wesentlichen technischen Daten.
- 检查交期、付款条件和送货地址。 / Prüfung von Lieferterminen, Zahlungsbedingungen und Lieferadressen.
- 标记缺失、额外或无法自动判断的项目。 / Kennzeichnung fehlender, zusätzlicher oder nicht automatisch bewertbarer Positionen.
- 生成适合人工复核的检查结果或报告。 / Erstellung von Prüfergebnissen oder Berichten für die manuelle Nachprüfung.

自动检查不能替代采购人员的最终审核。SAP 价格、付款条款、交期语义、送货地址和 OCR 结果必须人工确认。

Die automatische Prüfung ersetzt nicht die abschließende Prüfung durch den Einkauf. SAP-Preise, Zahlungsbedingungen, die Bedeutung von Lieferterminangaben, Lieferadressen und OCR-Ergebnisse müssen manuell bestätigt werden.

## 目录建议 / Empfohlene Verzeichnisstruktur

建议使用以下项目结构： / Empfohlen wird folgende Projektstruktur:

```text
abdaimler/
├── README.md
├── .gitignore
├── requirements.txt
├── *.py
├── private_input/       # 真实输入文件，仅保存在本地 / Echte Eingabedateien, nur lokal
├── private_output/      # 检查报告，仅保存在本地 / Prüfberichte, nur lokal
└── test_data/           # 仅完全脱敏或人工构造的数据 / Nur vollständig anonymisierte oder synthetische Testdaten
```

`private_input/` 和 `private_output/` 应加入 `.gitignore`。即使文件已被忽略，也应定期执行 `git status`，确认没有敏感资料进入暂存区。

Nehmen Sie `private_input/` und `private_output/` in die `.gitignore` auf. Führen Sie auch bei ignorierten Dateien regelmäßig `git status` aus, um sicherzustellen, dass keine sensiblen Daten in den Staging-Bereich gelangen.

## 1. 安装 Python / Python installieren

建议使用 Python 3.10 或更高版本，优先通过公司软件中心或公司批准的软件源安装。

Empfohlen wird Python 3.10 oder höher. Installieren Sie Python vorzugsweise über das Softwarecenter des Unternehmens oder eine vom Unternehmen freigegebene Softwarequelle.

### Windows

安装后打开 PowerShell，检查版本： / Öffnen Sie nach der Installation PowerShell und prüfen Sie die Versionen:

```powershell
python --version
python -m pip --version
```

如果使用 Python Launcher： / Bei Verwendung des Python Launchers:

```powershell
py --version
py -m pip --version
```

### macOS

```bash
python3 --version
python3 -m pip --version
```

### Ubuntu 或 Debian / Ubuntu oder Debian

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version
```

如果公司限制管理员权限或外部软件源，请联系 IT，不要绕过公司安全策略。

Falls das Unternehmen Administratorrechte oder externe Softwarequellen einschränkt, wenden Sie sich an die IT. Umgehen Sie keine unternehmensinternen Sicherheitsrichtlinien.

## 2. 下载项目 / Projekt herunterladen

如果公司允许从 GitHub 获取代码，可使用：

Sofern das Unternehmen den Bezug von Code über GitHub erlaubt, können Sie folgende Befehle verwenden:

```bash
git clone https://github.com/giengenbw/abdaimler.git
cd abdaimler
```

也可以从 GitHub 下载 ZIP，解压后在项目目录中打开终端。

Alternativ können Sie das Projekt als ZIP-Datei von GitHub herunterladen, entpacken und ein Terminal im Projektverzeichnis öffnen.

克隆或下载项目时不应包含真实订单文件。真实业务文件必须单独保存在受控目录中。

Das geklonte oder heruntergeladene Projekt darf keine echten Bestelldokumente enthalten. Echte Geschäftsunterlagen müssen separat in einem zugriffsgeschützten Verzeichnis gespeichert werden.

## 3. 创建虚拟环境 / Virtuelle Umgebung erstellen

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### Windows 命令提示符 / Windows-Eingabeaufforderung

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
```

### macOS 或 Linux / macOS oder Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

激活成功后，终端提示符通常会显示 `(.venv)`。

Nach erfolgreicher Aktivierung erscheint in der Eingabeaufforderung üblicherweise `(.venv)`.

## 4. 安装 Python 依赖 / Python-Abhängigkeiten installieren

如果项目中已有 `requirements.txt`，执行：

Falls das Projekt bereits eine `requirements.txt` enthält, führen Sie folgenden Befehl aus:

```bash
python -m pip install -r requirements.txt
```

如果脚本主要读取 PDF，通常至少需要：

Wenn das Skript hauptsächlich PDF-Dateien einliest, wird in der Regel mindestens folgendes Paket benötigt:

```bash
python -m pip install pypdf
```

如需创建 `requirements.txt`，可先使用以下内容：

Falls eine `requirements.txt` erstellt werden muss, kann zunächst folgender Eintrag verwendet werden:

```text
pypdf>=5,<7
```

正式使用时建议固定经过测试的精确版本，并在依赖升级后使用脱敏文件重新测试。

Für den produktiven Einsatz sollten exakt getestete Paketversionen festgelegt werden. Testen Sie nach Aktualisierungen der Abhängigkeiten erneut mit anonymisierten Dateien.

验证 `pypdf`： / Installation von `pypdf` prüfen:

```bash
python -c "import pypdf; print(pypdf.__version__)"
```

## 5. 可选安装：Poppler / Optionale Installation: Poppler

部分 Daimler PDF 的表格布局使用 `pdftotext -layout` 提取会更准确。`pdftotext` 属于 Poppler 工具集。

Bei einigen Daimler-PDFs lässt sich die Tabellenstruktur mit `pdftotext -layout` genauer extrahieren. `pdftotext` gehört zum Poppler-Werkzeugpaket.

### Windows

建议通过公司软件中心安装。安装后验证：

Die Installation über das Softwarecenter des Unternehmens wird empfohlen. Prüfen Sie anschließend die Installation:

```powershell
pdftotext -v
```

### macOS

如果公司允许使用 Homebrew： / Sofern Homebrew im Unternehmen freigegeben ist:

```bash
brew install poppler
pdftotext -v
```

### Ubuntu 或 Debian / Ubuntu oder Debian

```bash
sudo apt install poppler-utils
pdftotext -v
```

如果未安装 Poppler，脚本可根据自身实现回退到 `pypdf`，但复杂表格的提取质量可能下降。

Ist Poppler nicht installiert, kann das Skript je nach Implementierung auf `pypdf` zurückgreifen. Bei komplexen Tabellen kann dadurch die Extraktionsqualität sinken.

## 6. 可选安装：本地 OCR / Optionale Installation: lokale OCR

扫描 PDF 没有可搜索文本时，可在本机安装 OCRmyPDF 和 Tesseract。

Wenn gescannte PDFs keinen durchsuchbaren Text enthalten, können OCRmyPDF und Tesseract lokal installiert werden.

### Ubuntu 或 Debian / Ubuntu oder Debian

```bash
sudo apt install tesseract-ocr tesseract-ocr-deu ocrmypdf
```

### macOS

```bash
brew install tesseract ocrmypdf
```

### Windows

建议由 IT 通过公司批准的软件源安装：

Die Installation sollte durch die IT über vom Unternehmen freigegebene Softwarequellen erfolgen:

- Tesseract OCR
- OCRmyPDF
- Ghostscript 及相关组件 / Ghostscript und zugehörige Komponenten

验证： / Installation prüfen:

```bash
tesseract --version
ocrmypdf --version
```

不要将公司 PDF 上传到在线 OCR 或在线 PDF 转换服务。

Laden Sie Unternehmens-PDFs nicht auf Online-OCR-Dienste oder Online-PDF-Konverter hoch.

## 7. 运行脚本 / Skript ausführen

先查看仓库中的 Python 文件： / Zeigen Sie zunächst die Python-Dateien im Repository an:

### Windows PowerShell

```powershell
Get-ChildItem *.py
```

### macOS 或 Linux / macOS oder Linux

```bash
ls -1 *.py
```

查看目标脚本的帮助。以下命令中的 `SKRIPTNAME.py` 是占位符，请替换为实际脚本文件名：

Rufen Sie die Hilfe des gewünschten Skripts auf. `SKRIPTNAME.py` ist in den folgenden Befehlen ein Platzhalter und muss durch den tatsächlichen Skriptdateinamen ersetzt werden:

```bash
python SKRIPTNAME.py --help
```

如果主脚本采用“Bestellunterlagen + AB + 输出文件名”的参数形式，运行方式通常如下：

Wenn das Hauptskript die Parameter „Bestellunterlagen + AB + Ausgabedateiname“ verwendet, sieht der Aufruf üblicherweise wie folgt aus:

```bash
python SKRIPTNAME.py private_input/BESTELLUNG.pdf private_input/AB.pdf -o private_output/AB_Check_Report
```

Windows 示例： / Beispiel für Windows:

```powershell
python SKRIPTNAME.py private_input\BESTELLUNG.pdf private_input\AB.pdf -o private_output\AB_Check_Report
```

请以脚本的 `--help` 输出为准，不要仅根据 README 猜测参数。

Maßgeblich ist die `--help`-Ausgabe des Skripts. Leiten Sie die tatsächlichen Parameter nicht allein aus dieser README ab.

## 8. 运行前语法检查 / Syntaxprüfung vor der Ausführung

从网页或聊天工具复制 Python 代码时，运算符可能被转义为 HTML 实体，例如 `&lt;`、`&gt;` 或 `-&gt;`。保存后应先执行：

Beim Kopieren von Python-Code aus Webseiten oder Chat-Anwendungen können Operatoren als HTML-Entitäten wie `&lt;`, `&gt;` oder `-&gt;` übernommen werden. Führen Sie nach dem Speichern zunächst folgende Prüfung aus:

```bash
python -m py_compile SKRIPTNAME.py
```

命令没有输出通常表示语法检查通过。

Wenn der Befehl keine Ausgabe erzeugt, wurde die Syntaxprüfung in der Regel erfolgreich abgeschlossen.

例如，Python 文件中必须是： / Beispiel für die korrekte Schreibweise in einer Python-Datei:

```python
if visible >= 200:
    return pages
```

不能是： / Nicht korrekt ist:

```text
if visible &gt;= 200:
```

## 9. 结果状态说明 / Erläuterung der Ergebnisstatus

项目脚本可能使用以下状态： / Die Projektskripte können folgende Status verwenden:

- **OK**：自动检查结果一致。 / Die automatisch geprüften Angaben stimmen überein.
- **ERROR**：发现明确差异或缺失内容。 / Eindeutige Abweichungen oder fehlende Inhalte wurden festgestellt.
- **WARNING**：未能可靠提取，或只能宽松比较。 / Angaben konnten nicht zuverlässig extrahiert oder nur anhand weniger strenger Kriterien verglichen werden.
- **REVIEW**：必须人工核验。 / Eine manuelle Prüfung ist erforderlich.

建议对所有 ERROR、WARNING 和 REVIEW 项逐项打开原始文件进行确认。

Prüfen Sie alle mit ERROR, WARNING oder REVIEW gekennzeichneten Punkte einzeln anhand der Originaldateien.

## 10. 人工复核清单 / Checkliste für die manuelle Nachprüfung

即使程序没有报告明确错误，也应检查：

Auch wenn das Programm keine eindeutigen Fehler meldet, sind folgende Punkte zu prüfen:

- SAP 中最终订单价格是否与 AB 一致。 / Stimmt der endgültige Bestellpreis in SAP mit der AB überein?
- Angebotsnummer、Bestellnummer 和 Kundenbestellung 是否对应正确版本。 / Gehören Angebotsnummer, Bestellnummer und Kundenbestellung zur richtigen Version?
- 车辆型号、轴距、发动机功率和重量是否正确。 / Sind Fahrzeugtyp, Radstand, Motorleistung und Gewichtsangaben korrekt?
- 每个必须 Code 是否存在，Code 描述是否匹配。 / Sind alle erforderlichen Ausstattungscodes vorhanden und stimmen die Beschreibungen überein?
- AB 中额外 Code 是否会影响价格、交期或车辆配置。 / Beeinflussen zusätzliche Codes in der AB den Preis, den Liefertermin oder die Fahrzeugkonfiguration?
- 付款条件是否新增预付款、vor Zulassung 或其他限制。 / Enthalten die Zahlungsbedingungen zusätzliche Vorgaben wie Vorauszahlung, Zahlung „vor Zulassung“ oder andere Einschränkungen?
- 公司名称、街道、邮编、城市和 Tor 信息是否正确。 / Sind Firmenname, Straße, Postleitzahl, Ort und Torangaben korrekt?
- 交期中的月份、周次、年份和“预计/不具约束力”等语义是否一致。 / Stimmen Monat, Kalenderwoche, Jahr und die Bedeutung von Zusätzen wie „voraussichtlich“ oder „unverbindlich“ in den Lieferterminangaben überein?
- OCR 是否混淆 O/0、I/1、B/8 等字符。 / Hat die OCR Zeichen wie O/0, I/1 oder B/8 verwechselt?
- 包含多辆车、多版本或多个价格时，脚本是否提取了正确项目。 / Hat das Skript bei mehreren Fahrzeugen, Versionen oder Preisen die richtigen Angaben extrahiert?

## 11. 隐私保护要求 / Anforderungen an Vertraulichkeit und Datenschutz

### 输入文件 / Eingabedateien

以下内容不得提交到公开或未经批准的代码仓库：

Folgende Inhalte dürfen nicht in öffentliche oder nicht freigegebene Code-Repositories aufgenommen werden:

- Daimler Bestellunterlagen 和 AB PDF。 / Daimler-Bestellunterlagen und AB-PDFs.
- Excel 订单、价格表和 SAP 导出文件。 / Excel-Bestellungen, Preislisten und SAP-Exportdateien.
- 供应商报价和合同附件。 / Lieferantenangebote und Vertragsanlagen.
- 包含真实订单号、价格或地址的测试文件。 / Testdateien mit echten Bestellnummern, Preisen oder Adressen.
- PDF 页面截图和终端输出截图。 / Screenshots von PDF-Seiten und Terminal-Ausgaben.

### 输出文件 / Ausgabedateien

JSON、CSV、HTML、TXT 和日志可能包含：

JSON-, CSV-, HTML- und TXT-Dateien sowie Protokolle können folgende Angaben enthalten:

- 文件名和订单编号。 / Dateinamen und Bestellnummern.
- 车辆配置与 Code。 / Fahrzeugkonfigurationen und Ausstattungscodes.
- 采购价格和付款条件。 / Einkaufspreise und Zahlungsbedingungen.
- 客户、供应商和联系人信息。 / Kunden-, Lieferanten- und Kontaktdaten.
- 完整送货地址。 / Vollständige Lieferadressen.

输出报告应按照与原始订单相同的保护等级保存。分享前需要脱敏，并遵守公司信息保留和删除政策。

Ausgabeberichte sind mit demselben Schutzniveau wie die ursprünglichen Bestelldokumente zu speichern. Vor einer Weitergabe müssen sie anonymisiert werden. Die unternehmensinternen Aufbewahrungs- und Löschvorgaben sind einzuhalten.

### 安全测试数据 / Sichere Testdaten

开发时请使用人工构造或彻底脱敏的数据，例如：

Verwenden Sie für die Entwicklung synthetische oder vollständig anonymisierte Daten, beispielsweise:

```text
订单号 / Bestellnummer: TEST-001
报价号 / Angebotsnummer: ANGEBOT-TEST
公司名 / Firmenname: Musterfirma GmbH
联系人 / Kontaktperson: Max Mustermann
金额 / Betrag: 非真实测试金额 / Fiktiver Testbetrag
地址 / Adresse: 虚构测试地址 / Fiktive Testadresse
```

仅遮挡 PDF 的可见区域可能无法真正删除文本层、批注、附件或元数据。分享测试文件前，应使用公司批准的脱敏工具，并重新提取文字确认原信息已删除。

Das bloße Abdecken sichtbarer PDF-Bereiche entfernt möglicherweise weder die Textebene noch Kommentare, Anhänge oder Metadaten. Verwenden Sie vor der Weitergabe von Testdateien ein vom Unternehmen freigegebenes Anonymisierungswerkzeug und extrahieren Sie den Text erneut, um zu prüfen, ob die ursprünglichen Informationen tatsächlich entfernt wurden.

## 12. Git 安全检查 / Sicherheitsprüfung in Git

提交前执行： / Vor einem Commit ausführen:

```bash
git status
```

查看准备提交的文件： / Für den Commit vorgemerkte Dateien anzeigen:

```bash
git diff --cached --name-only
```

如果敏感文件已加入暂存区但尚未提交：

Falls eine sensible Datei bereits im Staging-Bereich liegt, aber noch nicht committet wurde:

```bash
git restore --staged path/to/sensitive-file.pdf
```

如果敏感文件已经被 Git 跟踪，但需要保留本地副本：

Falls eine sensible Datei bereits von Git verfolgt wird, die lokale Kopie jedoch erhalten bleiben soll:

```bash
git rm --cached path/to/sensitive-file.pdf
```

`.gitignore` 不能清除已经存在于 Git 历史中的文件。如果敏感文件已推送到远程仓库，应立即停止分享，联系公司 IT、信息安全或数据保护负责人，并按公司流程清理历史记录和远程副本。

Die `.gitignore` entfernt keine Dateien aus der bereits bestehenden Git-Historie. Wurden sensible Dateien bereits in ein Remote-Repository übertragen, stellen Sie die Weitergabe unverzüglich ein. Kontaktieren Sie die IT, die Informationssicherheit oder die zuständige Datenschutzstelle und bereinigen Sie die Historie sowie entfernte Kopien gemäß den Unternehmensprozessen.

## 13. 常见问题 / Häufige Probleme

### 缺少 pypdf / pypdf fehlt

```bash
python -m pip install pypdf
```

请确认虚拟环境已经激活，并使用当前 Python 对应的 `python -m pip`。

Stellen Sie sicher, dass die virtuelle Umgebung aktiviert ist, und verwenden Sie `python -m pip` der aktuell verwendeten Python-Installation.

### PDF 几乎没有可提取文本 / Aus der PDF lässt sich kaum Text extrahieren

该 PDF 可能是扫描件。请使用本机 OCR，或通过公司批准的软件转换为可搜索 PDF。不要使用在线 OCR 服务。

Möglicherweise handelt es sich um eine gescannte PDF. Verwenden Sie lokale OCR oder eine vom Unternehmen freigegebene Software, um eine durchsuchbare PDF zu erstellen. Nutzen Sie keine Online-OCR-Dienste.

### 金额、技术参数或 Code 提取错误 / Fehler bei der Extraktion von Beträgen, technischen Daten oder Codes

常见原因： / Häufige Ursachen:

- PDF 表格布局或嵌入字体特殊。 / Besonderheiten im PDF-Tabellenlayout oder bei eingebetteten Schriftarten.
- OCR 识别错误。 / OCR-Erkennungsfehler.
- 一个文件包含多个金额或车型。 / Mehrere Beträge oder Fahrzeugtypen in einer Datei.
- Daimler 文档模板发生变化。 / Änderungen an Daimler-Dokumentvorlagen.
- 字段名称与脚本中的正则表达式不匹配。 / Feldbezeichnungen passen nicht zu den regulären Ausdrücken im Skript.

应对照 PDF 原文人工确认，不要仅凭自动结果联系供应商或修改 SAP 订单。

Prüfen Sie die Angaben manuell anhand der Original-PDF. Kontaktieren Sie Lieferanten oder ändern Sie SAP-Bestellungen nicht allein auf Grundlage der automatischen Ergebnisse.

### HTML 或 CSV 报告不能公开分享 / HTML- oder CSV-Berichte dürfen nicht öffentlich geteilt werden

报告可能包含与原始 PDF 相同的敏感信息。即使没有附上 PDF，报告本身也必须按公司机密文件处理。

Berichte können dieselben sensiblen Informationen wie die ursprüngliche PDF enthalten. Auch ohne beigefügte PDF ist der Bericht selbst als vertrauliches Unternehmensdokument zu behandeln.

## 14. 已知限制 / Bekannte Einschränkungen

- 工具不能直接核对 SAP 中的数据，除非项目另有经过批准的接口。 / Das Werkzeug kann SAP-Daten nicht direkt abgleichen, sofern das Projekt nicht über eine gesondert freigegebene Schnittstelle verfügt.
- 自动提取依赖 Daimler 文档格式，模板变化后可能失效。 / Die automatische Extraktion hängt vom Daimler-Dokumentformat ab und kann nach Vorlagenänderungen fehlschlagen.
- OCR 可能错误识别 Code、金额、地址和日期。 / OCR kann Codes, Beträge, Adressen und Datumsangaben falsch erkennen.
- 文本相同不一定代表业务含义相同，文本不同也不一定代表业务冲突。 / Identische Texte bedeuten nicht zwangsläufig dieselbe geschäftliche Bedeutung. Unterschiedliche Texte stellen umgekehrt nicht zwangsläufig einen geschäftlichen Widerspruch dar.
- 多订单、多车辆和多版本文件可能需要人工拆分后检查。 / Dateien mit mehreren Bestellungen, Fahrzeugen oder Versionen müssen gegebenenfalls vor der Prüfung manuell aufgeteilt werden.
- 自动结果仅用于辅助，不构成合同、价格、交期或技术配置的最终确认。 / Automatische Ergebnisse dienen ausschließlich der Unterstützung und stellen keine abschließende Bestätigung von Verträgen, Preisen, Lieferterminen oder technischen Konfigurationen dar.

## 15. 快速开始 / Schnellstart

### Windows PowerShell

```powershell
git clone https://github.com/giengenbw/abdaimler.git
cd abdaimler
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Get-ChildItem *.py
python SKRIPTNAME.py --help
```

如果仓库没有 `requirements.txt`，用以下命令替代对应的依赖安装步骤：

Falls das Repository keine `requirements.txt` enthält, ersetzen Sie den entsprechenden Installationsschritt durch:

```powershell
python -m pip install pypdf
```

### macOS 或 Linux / macOS oder Linux

```bash
git clone https://github.com/giengenbw/abdaimler.git
cd abdaimler
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ls -1 *.py
python SKRIPTNAME.py --help
```

如果仓库没有 `requirements.txt`，用以下命令替代对应的依赖安装步骤：

Falls das Repository keine `requirements.txt` enthält, ersetzen Sie den entsprechenden Installationsschritt durch:

```bash
python -m pip install pypdf
```

`SKRIPTNAME.py` 为占位符，须替换为实际脚本文件名。

`SKRIPTNAME.py` ist ein Platzhalter und muss durch den tatsächlichen Skriptdateinamen ersetzt werden.

## 责任说明 / Verantwortungshinweis

本项目是内部辅助工具。自动检查中的“通过”仅表示脚本在可提取文本和当前规则范围内未发现差异，不代表订单、合同、价格、交期或车辆技术配置已经获得最终确认。最终放单、SAP 操作和供应商澄清必须由具有相应权限的人员按照公司流程完成。

Dieses Projekt ist ein internes Hilfsmittel. Ein positives automatisches Prüfergebnis bedeutet lediglich, dass das Skript innerhalb des extrahierbaren Textes und der aktuellen Prüfregeln keine Abweichungen festgestellt hat. Es stellt keine abschließende Bestätigung der Bestellung, des Vertrags, des Preises, des Liefertermins oder der technischen Fahrzeugkonfiguration dar. Die endgültige Bestellfreigabe, SAP-Bearbeitung und Klärung mit Lieferanten müssen durch entsprechend berechtigte Personen gemäß den Unternehmensprozessen erfolgen.
