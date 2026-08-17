# Daimler AB 自动检查工具

本项目用于在本地比较 Daimler 的 **Bestellunterlagen（订购资料）** 与 **Auftragsbestätigung，简称 AB（订单确认书）**，辅助采购人员检查订单编号、车辆配置、价格、技术参数、交期、付款条件以及送货信息。

> **重要：公司隐私与数据保护**
>
> 订单、报价、车辆配置、采购价格、客户编号、供应商信息、联系人和送货地址可能属于公司机密或个人信息。请仅在公司授权的设备和目录中运行本工具。不要将真实 PDF、Excel、检查报告、终端截图或处理结果提交到 GitHub，也不要上传至公共云盘、在线 OCR、在线 PDF 转换网站或未经公司批准的 AI 服务。

## 功能概览

根据项目中实际使用的脚本，工具可用于以下辅助检查：

- 读取 Daimler Bestellunterlagen 和 AB 文件
- 提取订单号、报价号或客户订单号
- 比较车辆配置 Code
- 检查净价和主要技术参数
- 检查交期、付款条件和送货地址
- 标记缺失、额外或无法自动判断的项目
- 生成适合人工复核的检查结果或报告

自动检查不能替代采购人员的最终审核。SAP 价格、付款条款、交期语义、送货地址和 OCR 结果必须人工确认。

## 目录建议

建议使用以下项目结构：

```text
abdaimler/
├── README.md
├── .gitignore
├── requirements.txt
├── *.py
├── private_input/       # 真实输入文件，仅保存在本地
├── private_output/      # 检查报告，仅保存在本地
└── test_data/           # 只能放完全脱敏或人工构造的测试资料
```

`private_input/` 和 `private_output/` 应加入 `.gitignore`。即使文件已被忽略，也应定期执行 `git status`，确认没有敏感资料进入暂存区。

## 1. 安装 Python

建议使用 Python 3.10 或更高版本，优先通过公司软件中心或公司批准的软件源安装。

### Windows

安装后打开 PowerShell，检查版本：

```powershell
python --version
python -m pip --version
```

如果使用 Python Launcher：

```powershell
py --version
py -m pip --version
```

### macOS

```bash
python3 --version
python3 -m pip --version
```

### Ubuntu 或 Debian

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
python3 --version
```

如果公司限制管理员权限或外部软件源，请联系 IT，不要绕过公司安全策略。

## 2. 下载项目

如果公司允许从 GitHub 获取代码，可使用：

```bash
git clone https://github.com/giengenbw/abdaimler.git
cd abdaimler
```

也可以从 GitHub 下载 ZIP，解压后在项目目录中打开终端。

> 克隆或下载项目时不应包含真实订单文件。真实业务文件必须单独保存在受控目录中。

## 3. 创建虚拟环境

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### Windows 命令提示符

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
```

### macOS 或 Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

激活成功后，终端提示符通常会显示 `(.venv)`。

## 4. 安装 Python 依赖

如果项目中已有 `requirements.txt`，执行：

```bash
python -m pip install -r requirements.txt
```

如果脚本主要读取 PDF，通常至少需要：

```bash
python -m pip install pypdf
```

如需创建 `requirements.txt`，可先使用：

```text
pypdf>=5,<7
```

正式使用时建议固定经过测试的精确版本，并在依赖升级后使用脱敏文件重新测试。

验证 `pypdf`：

```bash
python -c "import pypdf; print(pypdf.__version__)"
```

## 5. 可选安装：Poppler

部分 Daimler PDF 的表格布局使用 `pdftotext -layout` 提取会更准确。`pdftotext` 属于 Poppler 工具集。

### Windows

建议通过公司软件中心安装。安装后验证：

```powershell
pdftotext -v
```

### macOS

如果公司允许使用 Homebrew：

```bash
brew install poppler
pdftotext -v
```

### Ubuntu 或 Debian

```bash
sudo apt install poppler-utils
pdftotext -v
```

如果未安装 Poppler，脚本可根据自身实现回退到 `pypdf`，但复杂表格的提取质量可能下降。

## 6. 可选安装：本地 OCR

扫描 PDF 没有可搜索文本时，可在本机安装 OCRmyPDF 和 Tesseract。

### Ubuntu 或 Debian

```bash
sudo apt install tesseract-ocr tesseract-ocr-deu ocrmypdf
```

### macOS

```bash
brew install tesseract ocrmypdf
```

### Windows

建议由 IT 通过公司批准的软件源安装：

- Tesseract OCR
- OCRmyPDF
- Ghostscript及相关组件

验证：

```bash
tesseract --version
ocrmypdf --version
```

不要将公司 PDF 上传到在线 OCR 或在线 PDF 转换服务。

## 7. 运行脚本

先查看仓库中的 Python 文件：

### Windows PowerShell

```powershell
Get-ChildItem *.py
```

### macOS 或 Linux

```bash
ls -1 *.py
```

查看目标脚本的帮助：

```bash
python 脚本名称.py --help
```

如果主脚本采用“Bestellunterlagen + AB + 输出文件名”的参数形式，运行方式通常如下：

```bash
python 脚本名称.py private_input/BESTELLUNG.pdf private_input/AB.pdf -o private_output/AB_Check_Report
```

Windows 示例：

```powershell
python 脚本名称.py private_input\BESTELLUNG.pdf private_input\AB.pdf -o private_output\AB_Check_Report
```

请以脚本的 `--help` 输出为准，不要仅根据 README 猜测参数。

## 8. 运行前语法检查

从网页或聊天工具复制 Python 代码时，运算符可能被转义为 HTML 实体，例如 `&lt;`、`&gt;` 或 `-&gt;`。保存后应先执行：

```bash
python -m py_compile 脚本名称.py
```

命令没有输出通常表示语法检查通过。

例如，Python 文件中必须是：

```python
if visible >= 200:
    return pages
```

不能是：

```text
if visible &gt;= 200:
```

## 9. 结果状态说明

项目脚本可能使用以下状态：

- `OK`：自动检查结果一致
- `ERROR`：发现明确差异或缺失内容
- `WARNING`：未能可靠提取，或只能宽松比较
- `REVIEW`：必须人工核验

建议对所有 `ERROR`、`WARNING` 和 `REVIEW` 项逐项打开原始文件进行确认。

## 10. 人工复核清单

即使程序没有报告明确错误，也应检查：

1. SAP 中最终订单价格是否与 AB 一致。
2. Angebotsnummer、Bestellnummer 和 Kundenbestellung 是否对应正确版本。
3. 车辆型号、轴距、发动机功率和重量是否正确。
4. 每个必须 Code 是否存在，Code 描述是否匹配。
5. AB 中额外 Code 是否会影响价格、交期或车辆配置。
6. 付款条件是否新增预付款、`vor Zulassung` 或其他限制。
7. 公司名称、街道、邮编、城市和 Tor 信息是否正确。
8. 交期中的月份、周次、年份和“预计/不具约束力”等语义是否一致。
9. OCR 是否混淆 `O/0`、`I/1`、`B/8` 等字符。
10. 包含多辆车、多版本或多个价格时，脚本是否提取了正确项目。

## 11. 隐私保护要求

### 输入文件

以下内容不得提交到公开或未经批准的代码仓库：

- Daimler Bestellunterlagen 和 AB PDF
- Excel 订单、价格表和 SAP 导出文件
- 供应商报价和合同附件
- 包含真实订单号、价格或地址的测试文件
- PDF 页面截图和终端输出截图

### 输出文件

JSON、CSV、HTML、TXT 和日志可能包含：

- 文件名和订单编号
- 车辆配置与 Code
- 采购价格和付款条件
- 客户、供应商和联系人信息
- 完整送货地址

输出报告应按照与原始订单相同的保护等级保存。分享前需要脱敏，并遵守公司信息保留和删除政策。

### 安全测试数据

开发时请使用人工构造或彻底脱敏的数据，例如：

```text
订单号：TEST-001
报价号：ANGEBOT-TEST
公司名：Musterfirma GmbH
联系人：Max Mustermann
金额：使用非真实测试金额
地址：使用虚构测试地址
```

仅遮挡 PDF 的可见区域可能无法真正删除文本层、批注、附件或元数据。分享测试文件前，应使用公司批准的脱敏工具，并重新提取文字确认原信息已删除。

## 12. Git 安全检查

提交前执行：

```bash
git status
```

查看准备提交的文件：

```bash
git diff --cached --name-only
```

如果敏感文件已加入暂存区但尚未提交：

```bash
git restore --staged path/to/sensitive-file.pdf
```

如果敏感文件已经被 Git 跟踪，但需要保留本地副本：

```bash
git rm --cached path/to/sensitive-file.pdf
```

`.gitignore` 不能清除已经存在于 Git 历史中的文件。如果敏感文件已推送到远程仓库，应立即停止分享，联系公司 IT、信息安全或数据保护负责人，并按公司流程清理历史记录和远程副本。

## 13. 常见问题

### 缺少 `pypdf`

```bash
python -m pip install pypdf
```

请确认虚拟环境已经激活，并使用当前 Python 对应的 `python -m pip`。

### PDF 几乎没有可提取文本

该 PDF 可能是扫描件。请使用本机 OCR，或通过公司批准的软件转换为可搜索 PDF。不要使用在线 OCR 服务。

### 金额、技术参数或 Code 提取错误

常见原因：

- PDF 表格布局或嵌入字体特殊
- OCR 识别错误
- 一个文件包含多个金额或车型
- Daimler 文档模板发生变化
- 字段名称与脚本中的正则表达式不匹配

应对照 PDF 原文人工确认，不要仅凭自动结果联系供应商或修改 SAP 订单。

### HTML 或 CSV 报告不能公开分享

报告可能包含与原始 PDF 相同的敏感信息。即使没有附上 PDF，报告本身也必须按公司机密文件处理。

## 14. 已知限制

- 工具不能直接核对 SAP 中的数据，除非项目另有经过批准的接口。
- 自动提取依赖 Daimler 文档格式，模板变化后可能失效。
- OCR 可能错误识别 Code、金额、地址和日期。
- 文本相同不一定代表业务含义相同，文本不同也不一定代表业务冲突。
- 多订单、多车辆和多版本文件可能需要人工拆分后检查。
- 自动结果仅用于辅助，不构成合同、价格、交期或技术配置的最终确认。

## 15. 快速开始

### Windows PowerShell

```powershell
git clone https://github.com/giengenbw/abdaimler.git
cd abdaimler
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Get-ChildItem *.py
python 脚本名称.py --help
```

如果仓库没有 `requirements.txt`：

```powershell
python -m pip install pypdf
```

### macOS 或 Linux

```bash
git clone https://github.com/giengenbw/abdaimler.git
cd abdaimler
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ls -1 *.py
python 脚本名称.py --help
```

如果仓库没有 `requirements.txt`：

```bash
python -m pip install pypdf
```

## 责任说明

本项目是内部辅助工具。自动检查中的“通过”仅表示脚本在可提取文本和当前规则范围内未发现差异，不代表订单、合同、价格、交期或车辆技术配置已经获得最终确认。最终放单、SAP 操作和供应商澄清必须由具有相应权限的人员按照公司流程完成。
