# 楽天 買い時ボット

楽天APIで「一人暮らし向け」商品の価格を毎日取得し、自前の価格履歴から
「過去30日最安値」「ポイント高倍率」を判定して、投稿文と買い時ページを自動生成します。
Python標準ライブラリのみで動きます（追加インストール不要）。

## 構成
| ファイル | 役割 |
|---|---|
| `dealbot/rakuten.py` | 楽天API（2026年新仕様）クライアント |
| `dealbot/db.py` | 価格履歴DB（SQLite: `data/prices.db`） |
| `dealbot/analyze.py` | お得判定（ポイント込み実質価格） |
| `dealbot/posts.py` | X向け投稿文の生成（冒頭に【PR】） |
| `dealbot/site.py` | 買い時ページ `docs/index.html` の生成 |
| `dealbot/xpost.py` | X投稿（任意・初期は無効） |
| `targets.json` | 追跡するキーワード（20語×5商品＝約100商品） |
| `run_daily.sh` / `com.dealbot.daily.plist` | Mac mini で毎朝7:30に自動実行 |

## セットアップ（初回のみ・PM作業）
1. **GitHub**: 公開リポジトリ `rakuten-deal-bot` を作成し、Settings → Pages で `main` ブランチの `/docs` を公開
   → URL例 `https://ユーザー名.github.io/rakuten-deal-bot/`
2. **楽天アフィリエイト**: 楽天会員でログインし、アフィリエイトIDを確認
3. **楽天ウェブサービス**: https://webservice.rakuten.co.jp/ でアプリ新規登録
   - 許可されたWebサイト: `https://ユーザー名.github.io`
   - 許可IPアドレス: 自宅の回線IP（確認: https://ifconfig.me ）。変わる場合はCIDR（例 `xxx.xxx.0.0/16`）
   - 発行された「アプリID」「アクセスキー（pk_〜）」を控える
4. `config.example.json` を `config.json` にコピーして、上記の値を記入
   - APIのバージョン番号は楽天のドキュメントで最新を確認して必要なら修正
5. ターミナルで動作確認
   ```
   cd "/Users/kojisuganuma/Claude/side job/rakuten-deal-bot"
   python3 -m dealbot.main discover   # 追跡商品を登録（約3分）
   python3 -m dealbot.main daily      # 価格取得・ページ生成
   open docs/index.html
   ```
6. 自動実行の登録
   ```
   chmod +x run_daily.sh
   cp com.dealbot.daily.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.dealbot.daily.plist
   ```

## 毎日の流れ（自動）
7:30 価格取得 → 判定 → `out/posts/日付.txt` に投稿文 → ページ更新 → GitHubへpush →（有効時）X投稿

## 運用の段階
- 1〜2週目: X投稿は無効のまま。`out/posts/` の文面を見て手動で投稿（反応確認）
- 3週目以降: X APIのクレジットを購入し、`config.json` の `x.enabled` を true

## 注意
- PR表記は投稿・ページとも冒頭に固定（楽天のステマ規制対応）
- 価格は取得時点のもの。ページと投稿に取得日と「変動します」を必ず表示
- 価格履歴が7日分たまるまでは「ポイント高倍率」のみ判定（最安値判定は8日目から、精度は30日で安定）
- `config.json` はキーを含むためGitにコミットしない（.gitignore済み）
- 動作テスト: `python3 -m dealbot.main discover --mock` / `daily --mock --date 2026-10-04`
