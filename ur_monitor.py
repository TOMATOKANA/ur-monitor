import os
import json
import time
import requests

# =========================
# 設定
# =========================

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
DISCORD_USER_ID = os.environ.get("DISCORD_USER_ID")
MENTION_ID = f"<@{DISCORD_USER_ID}>" if DISCORD_USER_ID else ""

# =========================
# UR地域コード
# =========================

CITIES = {
    "世田谷区": "13112",
    "中野区": "13114",
    "杉並区": "13115",
    "練馬区": "13120",
    "豊島区": "13116",
    "三鷹市": "13204",
    "武蔵野市": "13203",
    "調布市": "13208",
    "狛江市": "13219",
    "目黒区": "13110"
}

# =========================
# ★ここが重要（APIエンドポイント）
# =========================
# ⚠ 初回は必ずブラウザDevToolsで確認して差し替え前提
API_URL = "https://chintai.r6.ur-net.go.jp/api/search/result"

# =========================
# Discord通知
# =========================

def notify(msg):
    if not DISCORD_WEBHOOK:
        print(msg)
        return
    requests.post(DISCORD_WEBHOOK, json={"content": msg})

# =========================
# キャッシュ
# =========================

def load_cache():
    try:
        with open("cache.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_cache(data):
    with open("cache.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========================
# API取得（直叩き）
# =========================

def fetch_city(city_name, city_code):

    params = {
        "city[]": city_code
    }

    print(f"\n--- {city_name} ---")

    try:
        r = requests.get(API_URL, params=params, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print("HTTP ERROR:", e)
        return {}

    data = r.json()

    results = {}

    # =========================
    # 構造吸収（UR変動対策）
    # =========================

    items = (
        data.get("data")
        or data.get("properties")
        or data.get("result")
        or []
    )

    for item in items:

        name = item.get("name") or item.get("bukkenName") or "不明"
        count = item.get("vacancyCount") or item.get("count") or 0
        link = item.get("detailUrl") or ""

        if link and not link.startswith("http"):
            link = "https://chintai.r6.ur-net.go.jp" + link

        key = f"{city_name}:{name}"

        results[key] = {
            "count": int(count),
            "link": link
        }

    print("取得件数:", len(results))

    return results

# =========================
# メイン
# =========================

def main():

    old = load_cache()
    new = {}

    for city_name, city_code in CITIES.items():

        data = fetch_city(city_name, city_code)

        for k, v in data.items():

            new[k] = v

            old_count = old.get(k, {}).get("count", 0)

            if v["count"] > old_count:

                notify(
                    f"{MENTION_ID} 🆕空室増加\n"
                    f"{k}\n"
                    f"{old_count} → {v['count']}\n"
                    f"{v['link']}"
                )

        time.sleep(1)  # アクセス制御

    save_cache(new)

# =========================
# 実行
# =========================

if __name__ == "__main__":
    main()
