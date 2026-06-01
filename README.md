# daily-us-news-discord

每天自動收集可靠美國新聞來源的重要新聞，先做查證，再用繁體中文整理成「已查證每日美國新聞簡報」並送到 Discord。

這個專案不是內容創作工具。它不會產生社群貼文、hashtag、Threads 點子、Instagram 輪播點子或影片點子，也不會把簡報標成審稿草稿。若可靠且可查證的新聞少於 5 則，系統只會送出已查證的新聞，並清楚標示找到幾則。

## 功能

- 從 AP、Reuters US、NPR、The New York Times、The Washington Post、The Wall Street Journal、Axios、Politico、CNN、NBC News 等可靠美國新聞來源讀取新聞。
- 避免同一事件的重複新聞。
- 嘗試抓取原文內容，並用其他可靠來源比對同題報導。
- 每則新聞包含中文標題、英文原標題、來源、發布時間、URL、摘要、重點、重要性、實際意義與查證資訊。
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
OPENAI_API_KEY=你的 OpenAI API key
OPENAI_MODEL=gpt-4o-mini
MAX_ARTICLES=5
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

如果沒有設定 `OPENAI_API_KEY`，`--dry-run` 會使用備援摘要格式方便檢查流程；正式送出 Discord 時必須設定 `OPENAI_API_KEY`。

## GitHub Actions 設定

workflow 檔案位於：

```text
.github/workflows/daily-news.yml
```

它會在 GitHub runner 上自動安裝 Python 3.11，因此不需要在 GitHub 主機另外安裝 Python。

在 GitHub repository 加入 Secrets：

- `DISCORD_WEBHOOK_URL`
- `OPENAI_API_KEY`

可選擇加入 repository variable：

- `OPENAI_MODEL`，預設為 `gpt-4o-mini`

設定完成後，可以在 GitHub Actions 頁面使用 `Run workflow` 手動測試。

## GitHub 推送

如果這個資料夾還不是 git repository：

```powershell
git init
git add .
git commit -m "Initial daily US news Discord briefing"
git branch -M main
git remote add origin <GITHUB_REPO_URL>
git push -u origin main
```

請把 `<GITHUB_REPO_URL>` 換成你的既有 GitHub repository URL。

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
