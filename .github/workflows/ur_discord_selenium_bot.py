import time
import difflib
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# =========================
# 設定
# =========================
URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city[]=13110"

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1512593894292979763/rDqQiE18d0aBdLpZqOc9P3Z_prepaJz_SG1BU-_6S7oL-imeGooK5YvIinxJ5r1GGiYD"
MENTION_USER_ID = "329597244204515328"

INTERVAL_SECONDS = 300  # 5分

# =========================
# Seleniumセットアップ
# =========================
def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    return driver


# =========================
# 物件取得
# =========================
def fetch_properties(driver):
    print("ページ取得中...")
    driver.get(URL)
    time.sleep(5)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

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

        results.append({
            "name": name,
            "rooms": rooms,
            "url": link
        })

    return results


# =========================
# Discord通知（メンション付き）
# =========================
def send_discord_notification(item):
    content = f"<@{MENTION_USER_ID}>\n🚨 空室検出\n\n" \
              f"🏠 {item['name']}\n" \
              f"🛏 空室数: {item['rooms']}\n" \
              f"🔗 {item['url']}"

    data = {
        "content": content
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
        print("Discord送信成功:", item["name"])
    except Exception as e:
        print("Discord送信エラー:", e)


# =========================
# 差分検知
# =========================
def detect_changes(old, new):
    old_set = set([x["name"] for x in old])
    new_set = set([x["name"] for x in new])

    added = new_set - old_set

    return [x for x in new if x["name"] in added]


# =========================
# メインループ
# =========================
def main():
    driver = create_driver()

    print("初回取得完了")

    old_data = fetch_properties(driver)

    while True:
        time.sleep(INTERVAL_SECONDS)

        try:
            new_data = fetch_properties(driver)

            changes = detect_changes(old_data, new_data)

            if changes:
                print("変化検出:", len(changes))

                for item in changes:
                    send_discord_notification(item)

            else:
                print("変化なし")

            old_data = new_data

        except Exception as e:
            print("エラー:", e)


if __name__ == "__main__":
    main()
