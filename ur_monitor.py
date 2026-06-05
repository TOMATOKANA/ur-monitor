import requests
from bs4 import BeautifulSoup

# =========================
# 設定
# =========================
URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city[]=13110"

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1512593894292979763/rDqQiE18d0aBdLpZqOc9P3Z_prepaJz_SG1BU-_6S7oL-imeGooK5YvIinxJ5r1GGiYD"
MENTION_USER_ID = "329597244204515328"

# =========================
# 物件取得
# =========================
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
        name_tag = item.select_one(".rep_bukken-name")
        link_tag = item.select_one(".rep_bukken-link")
        room_tag = item.select_one(".rep_bukken-count-room")

        if not name_tag or not link_tag:
            continue

        name = name_tag.text.strip()
        link = "https://chintai.r6.ur-net.go.jp" + link_tag.get("href")
        rooms = room_tag.text.strip() if room_tag else "0"

        try:
            rooms_int = int(rooms)
        except:
            rooms_int = 0

        results.append({
            "name": name,
            "rooms": rooms_int,
            "url": link
        })

    return results


# =========================
# Discord通知（メンション付き）
# =========================
def notify(item):
    content = (
        f"<@{MENTION_USER_ID}>\n"
        f"🚨【UR空室更新】\n\n"
        f"🏠 物件: {item['name']}\n"
        f"🛏 空室数: {item['rooms']}\n"
        f"🔗 {item['url']}\n\n"
        f"⚡ 早めに確認してください"
    )

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content})
        print("通知送信:", item["name"])
    except Exception as e:
        print("通知エラー:", e)


# =========================
# 状態保存（ファイル）
# =========================
def load_state():
    state = {}

    try:
        with open("state.txt", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) != 2:
                    continue
                name, rooms = parts
                try:
                    state[name] = int(rooms)
                except:
                    state[name] = 0
    except:
        pass

    return state


def save_state(data):
    with open("state.txt", "w", encoding="utf-8") as f:
        for item in data:
            f.write(f"{item['name']}|{item['rooms']}\n")


# =========================
# メイン処理
# =========================
def main():
    print("UR監視開始")

    old_state = load_state()
    new_data = fetch()

    print(f"取得件数: {len(new_data)}")

    for item in new_data:
        name = item["name"]
        rooms = item["rooms"]

        old_rooms = old_state.get(name, 0)

        # 🔥 空室が0→1以上になったときだけ通知
        if old_rooms == 0 and rooms > 0:
            notify(item)

        # 初回 or 新規物件
        elif name not in old_state and rooms > 0:
            notify(item)

    save_state(new_data)

    print("完了")


if __name__ == "__main__":
    main()
