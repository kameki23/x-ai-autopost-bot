# X AI Case Bot (Basic API)

AI成功事例 + AIツール活用をテーマに、1つの記事を3分割してJST 09:00 / 13:00 / 20:00に投稿するPythonボットです。

## 特徴
- 収集: RSS + リストページURL
- 抽出: `readability-lxml` + `BeautifulSoup`
- ランキング: テーマ適合 / 実務性 / 人物関連
- 投稿文生成: 日本語解説者トーン（客観・知的・非煽り）
- 3スロット運用: 
  - slot1 朝: 導入
  - slot2 昼: 戦略
  - slot3 夜: 現代接続（**記事URL + 画像出典URL必須**）
- 重複回避: URL/hash/person/topic近似の重複チェック
- クールダウン / リトライ / ログ / SQLite状態管理
- 画像安全: `ALLOW_IMAGE=true` のときのみ人物顔画像使用。既定はノーフェイスカード。
- 既定は安全: `DRY_RUN=true`（**実投稿しない**）

## ディレクトリ
- `config/` 設定JSON
- `src/` 実装
- `data/bot.sqlite3` 状態DB
- `logs/bot.log`

## セットアップ
```bash
cd bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 実行
```bash
# 現在のJSTスロットのみ処理
python -m src.main

# スロット指定でテスト
python -m src.main --slot 1
python -m src.main --slot 2
python -m src.main --slot 3
```

## DRY_RUNと本番投稿
- デフォルト: `.env` の `DRY_RUN=true` でログ出力のみ
- 本番投稿する場合のみ明示的に:
```env
DRY_RUN=false
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
```

## ローカルcron例
JSTで 09:00 / 13:00 / 20:00 に実行する例:
```cron
0 9,13,20 * * * cd /path/to/bot && /path/to/bot/.venv/bin/python -m src.main >> logs/cron.log 2>&1
```

## GitHub Actions
`.github/workflows/bot.yml` は UTC cron で実行:
- 00:00 UTC (=09:00 JST)
- 04:00 UTC (=13:00 JST)
- 11:00 UTC (=20:00 JST)

必要Secrets:
- `DRY_RUN` (任意, 既定true)
- `ALLOW_IMAGE` (任意, 既定false)
- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

## Webダッシュボード（ローカル）
Flaskベースの簡易UIを `webapp/` に追加しています。

```bash
cd bot
python webapp/app.py
```

ブラウザで `http://127.0.0.1:5001` を開くと、以下を操作できます。
- `.env` のX APIキー編集（マスク表示）と `DRY_RUN` 切替
- 手動実行（slot1 / slot2 / slot3 / auto）
- `config/sources.json` / `config/people.json` / `config/rules.json` 編集
- `logs/*.log` の末尾表示
- SQLiteの最近投稿一覧と件数表示

## 補足
- 人物画像は `ALLOW_IMAGE=true` でのみ利用。
- slot3 投稿には常に記事出典と画像出典（または no-face-card）を含める仕様です。
- 例外時はリトライ/ログ記録し、致命的エラーは非0で終了します。
