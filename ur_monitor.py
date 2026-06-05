import requests
from bs4 import BeautifulSoup

URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city[]=13110"

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1512593894292979763/rDqQiE18d0aBdLpZqOc9P3Z_prepaJz_SG1BU-_6S7oL-imeGooK5YvIinxJ5r1GGiYD"
MENTION_USER_ID = "329597244204515328"


def fetch():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(URL, headers=headers, timeout=30)

    if res.status_code != 200:
        print("取得失敗:", res.status_code)
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    items = soup.select(".module_cassettes_property")

    results = []

    for item in items:
        name = item.select_one(".rep_bukken-name")
        link = item.select_one(".rep_bukken-link")
        room = item.select_one(".rep_bukken-count-room")

        if not name or not link:
            continue

        name = name.text.strip()
        link = "https://chintai.r6.ur-net.go.jp" + link["href"]
        room = room.text.strip() if room else "0"

        results.append({
            "name": name,
            "rooms": room,
            "url": link
        })

    return results


def notify(item):
    content = (
        f"<@{MENTION_USER_ID}>\n"
        f"🚨 UR空室検出\n\n"
        f"🏠 {item['name']}\n"
        f"🛏 空室: {item['rooms']}\n"
        f"🔗 {item['url']}"
    )

    requests.post(DISCORD_WEBHOOK_URL, json={"content": content})


def load_old():
    try:
        with open("old.txt", "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except:
        return set()


def save_new(data):
    with open("old.txt", "w", encoding="utf-8") as f:
        for item in data:
            f.write(item["name"] + "\n")


def main():
    print("取得開始")

    old = load_old()
    new_data = fetch()

    new_names = set([x["name"] for x in new_data])

    added = new_names - old

    for item in new_data:
        if item["name"] in added:
            notify(item)

    save_new(new_data)


if __name__ == "__main__":
    main()
