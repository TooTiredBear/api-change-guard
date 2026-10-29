# API Change Guard

[English](README.md) | [繁體中文](README.zh-TW.md)

在本機比較新舊 OpenAPI 規格，找出可能讓既有客戶端無法正常運作的變更。

例如：刪除 API 端點、將請求參數改為必填、移除必要的回應欄位，或變更回應型別。
工具會輸出 Markdown 摘要及退出碼，協助你在發布前檢查相容性。

目前是小型 POC，以 Python CLI 封裝 [oasdiff](https://github.com/oasdiff/oasdiff)。
相容性分析全部由上游引擎執行；本工具提供固定檢查選項、報告與一致的退出碼，
並非自行實作新的比較演算法，也不取代上游工具。

## 快速開始

需要 Python 3.11 以上版本及 oasdiff。在專案根目錄使用 Windows PowerShell 執行：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe scripts/install_oasdiff.py
.venv\Scripts\api-change-guard.exe check examples/base.json examples/compatible.json --oasdiff .tools/oasdiff.exe
.venv\Scripts\api-change-guard.exe check examples/base.json examples/breaking.json --oasdiff .tools/oasdiff.exe --report reports/breaking.md
```

Linux／macOS 請將對應路徑改為 `.venv/bin/python`、`.venv/bin/api-change-guard`
與 `.tools/oasdiff`。

安裝腳本固定下載 oasdiff **v1.34.1**，並使用上游公布的 SHA-256 驗證壓縮檔。
若執行檔已存在，腳本會拒絕覆寫。也可以自行安裝 oasdiff，使用 `--oasdiff`
指定執行檔路徑，或將它加入 `PATH`。

相容範例新增可選的回應欄位；不相容範例移除必要的 `customer_id` 回應欄位。
**最後一個指令預期回傳退出碼 `1`，表示偵測到不相容變更，不是工具故障。**

## 使用方式

```text
api-change-guard check BASE REVISION [--oasdiff PATH] [--report FILE]
```

- `BASE`：舊版規格。
- `REVISION`：預計採用的新版規格。
- `--oasdiff`：引擎的名稱或路徑，預設從 `PATH` 尋找 `oasdiff`。
- `--report`：選填，將摘要另存為 UTF-8 Markdown 檔案。

兩份輸入都必須是本機、自足的 OpenAPI 檔案，格式可為 JSON 或 YAML。
支援文件內部的 `$ref`，不允許參照外部檔案或網址。
FastAPI 專案可先將新舊版本的 `app.openapi()` 分別匯出為 JSON，再進行比較。

摘要會顯示在終端機。每次引擎執行限時 60 秒，使用明確的空白設定檔及
`--fail-on WARN`，因此警告與錯誤等級的不相容變更都會讓檢查不通過。

| 退出碼 | 意義 |
| --- | --- |
| 0 | 未偵測到不相容變更 |
| 1 | 偵測到不相容變更 |
| 2 | 無法完成檢查，例如輸入無效或缺少引擎 |

只有退出碼為 `0` 或 `1` 時，才能將報告視為本次檢查結果。
執行失敗時不會更新既有報告，請勿把舊報告誤認為最新結果。

## 範圍與限制

- 已測試端點移除、請求參數改為必填、必要回應欄位移除與回應型別不相容等情境。
- 比較的是規格，不會呼叫實際 API；無法保證執行期行為、權限、效能，或 AI 修改的正確性。
- 禁止外部參照不等於沙箱隔離。不可信的規格應在不含機密資訊的隔離環境中執行。
- 本工具不使用 AI 服務，不需要 API 金鑰，也不託管服務、收集遙測或上傳報告。
  安裝腳本會連線至 GitHub 下載引擎。

## 開發與驗證

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check src tests scripts
.venv\Scripts\python.exe -m build --no-isolation
```

當 `.tools/oasdiff[.exe]` 或 `PATH` 中有引擎時，整合測試會自動執行，否則會跳過。
可以透過 `OASDIFF_BINARY` 環境變數指定引擎路徑，要求使用該引擎。
單元測試不需要引擎。目前不包含 GitHub Actions workflow，請在本機執行檢查。

回報問題時，請提供去識別化的最小新舊規格、CLI 與引擎版本，以及預期結果。
不要提交憑證或私有 API 規格；若問題涉及相容性規則，也請確認上游 oasdiff 的行為。

## 授權

採用 Apache-2.0，詳見 [LICENSE](LICENSE)。oasdiff 為獨立專案，有其自己的授權。
本專案與 OpenAI 或 oasdiff 無隸屬關係。