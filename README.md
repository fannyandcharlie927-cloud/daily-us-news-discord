# daily-us-news-discord

每天自動收集可靠新聞來源的 AI 新聞，整理成「AI新聞」並送到 Discord。預設包含 5 篇 AI 軟體/硬體更新，以及 3 篇使用 AI 或 Codex 做出作品、App、工具或專案的案例。

這是免費版本，不使用 OpenAI API，也不需要付費 AI 額度。摘要與重點會嘗試使用免費翻譯端點轉成繁體中文；如果免費翻譯端點失敗，系統會保留英文原文，不會改用付費服務。

## 重要限制

- 不使用付費 AI 或翻譯 API，因此翻譯品質與可用性取決於免費翻譯端點。
- 系統會送出中文標題、英文原標題、來源、時間、URL、中文摘要、中文重點與兩段內文。
- 如果未來要完整繁體中文摘要與分析，需要接入 OpenAI API 或其他翻譯/摘要服務；這通常需要額度或付費。

## 功能

- 從 AP、Reuters US、NPR、The New York Times、The Washington Post、The Wall Street Journal、Axios、Politico、CNN、NBC News 等可靠新聞來源讀取 AI 相關新聞。
- 避免同一事件的重複新聞。
- 嘗試抓取原文內容，並用其他可靠來源比對同題報導。
- 每則新聞包含中文標題、英文原標題、來源、發布時間、URL、摘要、重點與兩段內文。
- 使用 `DISCORD_WEBHOOK_URL` 傳送到 Discord。
- Discord 訊息過長時會自動分段。
- GitHub Actions 每日自動執行，簡報日期與時間使用 `Australia/Hobart` 邏輯。

## Windows 本機安裝 Python

如果你的電腦執行 `python --version` 或 `py --version` 找不到 Python，請使用官方安裝程式：

1. 到 [Python 3.11 Windows downloads](https://www.python.org/downloads/windows/) 下載 Python 3.11 的 Windows installer。
2. 執行安裝程式。
3. 勾選 `Add python.exe to PATH`。
4. 選擇 `Install Now`。
5. 安裝完成後，重新開啟 PowerShell。
6. 確認版本：

```powershell
python --version
pip --version
```

建議使用 Python 3.11，因為 GitHub Actions workflow 也使用 Python 3.11。

## 本機設定

1. 建立虛擬環境並安裝套件：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. 建立 `.env`：

```powershell
copy .env.example .env
```

3. 在 `.env` 填入：

```text
DISCORD_WEBHOOK_URL=你的 Discord webhook
MAX_ARTICLES=8
LOCAL_TIMEZONE=Australia/Hobart
```

不要把 `.env` 提交到 GitHub。

## 手動測試

只產生簡報、不送 Discord：

```powershell
python -m news_briefing.main --dry-run
```

實際送到 Discord：

```powershell
python -m news_briefing.main
```

## GitHub Actions 設定

workflow 檔案位於：

```text
.github/workflows/daily-news.yml
```

它會在 GitHub runner 上自動安裝 Python 3.11，因此不需要在 GitHub 主機另外安裝 Python。

在 GitHub repository 加入 Secret：

- `DISCORD_WEBHOOK_URL`

不需要設定 `OPENAI_API_KEY`。

設定完成後，可以在 GitHub Actions 頁面使用 `Run workflow` 手動測試。

## 查證邏輯

系統會先確認新聞來自設定的可靠來源，再嘗試讀取原文頁面，並搜尋最近兩天內其他可靠媒體是否有同題報導。

信心等級：

- `High`：有原文內容，且至少兩個支持來源。
- `Medium`：有原文、RSS 摘要或至少一個支持來源。
- `Low`：資訊不足，不會被納入正式簡報。

若支持來源有限，簡報會在該則新聞的提醒欄位標示。

## UTF-8 顯示

`README.md` 使用 UTF-8 編碼。如果 PowerShell 顯示亂碼，可以先執行：

```powershell
chcp 65001
Get-Content README.md -Encoding UTF8
```

這只影響終端機顯示，不影響 GitHub 或編輯器中的文件內容。

## 注意事項

- 部分新聞網站可能有付費牆或阻擋自動抓取，系統會改用 RSS 摘要與可用支持來源。
- GitHub Actions 的 cron 使用 UTC；程式內部會用 `Australia/Hobart` 產生日期與時間，因此能處理當地時區與日光節約時間。
- 系統不會補寫不存在的新聞，也不會為了湊滿 5 則而使用未通過查證的項目。
