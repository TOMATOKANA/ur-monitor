import requests
from bs4 import BeautifulSoup

# =========================
# 設定
# =========================
URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city%5B%5D=13110"

DISCORD_WEBHOOK = ""  # GitHub Secrets運用推奨（後で説明）
MENTION_ID = ""       # 例: <@1234567890>

# =========================
# 取得処理
# =========================
def fetch():

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    print("ページ取得中...")

    r = requests.get(URL, headers=headers, timeout=20)

    print("HTTP STATUS:", r.status_code)

    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    # 物件カード
    cards = soup.select(".module_cassettes_property")

    print("取得件数:", len(cards))

    for card in cards:

        name_tag = card.select_one(".rep_bukken-name")
        count_tag = card.select_one(".rep_bukken-count-room")
        link_tag = card.select_one("a.rep_bukken-link")

        if not name_tag:
            continue

        name = name_tag.get_text(strip=True)

        # 空室数
        try:
            count = int(count_tag.get_text(strip=True))
        except:
            count = 0

        # URL
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
def notify(message: str):

    if not DISCORD_WEBHOOK:
        print("Webhook未設定のため通知スキップ")
        return

    payload = {
        "content": message
    }

    requests.post(DISCORD_WEBHOOK, json=payload)


# =========================
# メイン処理
# =========================
def main():

    data = fetch()

    print("取得物件一覧")
    print("=" * 50)

    for item in data:
        name = item["name"]
        count = item["count"]
        link = item["link"]

        print(f"物件名 : {name}")
        print(f"空室数 : {count}")
        print("-" * 50)

        # 通知条件
        if count > 0:
            msg = f"{MENTION_ID} 🆕空室あり: {name}（{count}件）\n{link}"
            notify(msg)


# =========================
# 実行
# =========================
if __name__ == "__main__":
    main()
