import requests
import json
import time
from bs4 import BeautifulSoup

# =========================
# 設定
# =========================
SEARCH_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city%5B%5D=13110"

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1512593894292979763/rDqQiE18d0aBdLpZqOc9P3Z_prepaJz_SG1BU-_6S7oL-imeGooK5YvIinxJ5r1GGiYD"  # GitHub Secrets推奨
MENTION_ID = "329597244204515328"       # <@ユーザーID>

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://chintai.r6.ur-net.go.jp/",
}


# =========================
# 物件取得（API探索＋HTMLフォールバック）
# =========================
def fetch_properties():

    print("API探索中...")

    r = requests.get(SEARCH_URL, headers=HEADERS, timeout=20)

    print("HTTP STATUS:", r.status_code)

    r.raise_for_status()

    # ---------------------------------
    # ① JSON APIが埋まっている場合を探索
    # ---------------------------------
    try:
        data = r.json()

        # もしJSONならここで処理
        if isinstance(data, dict):
            print("JSON API検出")

            results = []

            for item in data.get("result", []):
                name = item.get("name")
                count = item.get("vacancyCount", 0)
                link = item.get("detailUrl", "")

                results.append({
                    "name": name,
                    "count": count,
                    "link": link
                })

            return results

    except:
        pass

    # ---------------------------------
    # ② HTML解析（通常はこちら）
    # ---------------------------------

    print("HTML解析モード")

    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    cards = soup.select(".module_cassettes_property")

    print("取得件数:", len(cards))

    for card in cards:

        name_tag = card.select_one(".rep_bukken-name")
        count_tag = card.select_one(".rep_bukken-count-room")
        link_tag = card.select_one("a.rep_bukken-link")

        if not name_tag:
            continue

        name = name_tag.get_text(strip=True)

        try:
            count = int(count_tag.get_text(strip=True))
        except:
            count = 0

        link = ""
        if link_tag and link_tag.get("href"):
            link = "https://chintai.r6.ur-net.go.jp" + link_tag["href"]

        results.append({
            "name": name,
            "count": count,
            "link": link
        })

    return results


# =========================
# Discord通知
# =========================
def notify(msg):

    if not DISCORD_WEBHOOK:
        print("Webhook未設定")
        return

    payload = {
        "content": msg
    }

    requests.post(DISCORD_WEBHOOK, json=payload)


# =========================
# 差分管理（取りこぼし防止）
# =========================
def load_cache():
    try:
        with open("cache.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_cache(cache):
    with open("cache.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# =========================
# メイン
# =========================
def main():

    old_cache = load_cache()
    new_cache = {}

    data = fetch_properties()

    print("取得結果")
    print("=" * 50)

    for item in data:

        name = item["name"]
        count = item["count"]
        link = item["link"]

        print(f"{name} / {count}")

        new_cache[name] = count

        old_count = old_cache.get(name, 0)

        # -------------------------
        # 差分検知（ここが重要）
        # -------------------------
        if count > old_count:

            msg = (
                f"{MENTION_ID} 🆕空室増加検知\n"
                f"{name}\n"
                f"前: {old_count} → 現在: {count}\n"
                f"{link}"
            )

            notify(msg)

    save_cache(new_cache)


if __name__ == "__main__":
    main()
