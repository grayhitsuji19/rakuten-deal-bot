#!/bin/bash
# 毎日1回: 価格取得 → 判定 → 投稿文・ページ生成 →（任意）GitHub Pagesへ公開 →（任意）X投稿
set -u
cd "$(dirname "$0")"
mkdir -p logs
LOG="logs/$(date +%Y-%m-%d).log"
{
  echo "=== $(date) ==="
  # スリープ復帰直後はネットワークが未接続のことがあるため、最大5分待つ
  for i in $(seq 1 30); do
    /usr/bin/curl -4 -s -o /dev/null --max-time 5 https://openapi.rakuten.co.jp/ && break
    sleep 10
  done
  # 毎週日曜: 追跡商品を補充（販売終了分の入れ替え・targets.json の追加キーワード反映）
  if [ "$(date +%u)" = "7" ]; then
    /usr/bin/python3 -m dealbot.main discover
  fi
  OUT=$(/usr/bin/python3 -m dealbot.main daily 2>&1); echo "$OUT"
  OK=$(echo "$OUT" | sed -n 's/.*価格取得: 成功 \([0-9]*\).*/\1/p')
  if [ -z "$OK" ] || [ "$OK" -lt 50 ]; then
    /usr/bin/osascript -e 'display notification "価格取得に失敗しました。Claudeに「動いてる？」と聞いてください" with title "楽天 買い時ボット" sound name "Basso"'
  fi
  if [ -d .git ]; then
    git add docs/index.html && git commit -q -m "update $(date +%Y-%m-%d)" && git push -q
  fi
  /usr/bin/python3 -m dealbot.main post
} >> "$LOG" 2>&1
