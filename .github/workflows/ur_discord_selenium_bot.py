import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# =========================
# 設定
# =========================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1512593894292979763/rDqQiE18d0aBdLpZqOc9P3Z_prepaJz_SG1BU-_6S7oL-imeGooK5YvIinxJ5r1GGiYD"
DISCORD_USER_ID = "329597244204515328"

TARGET_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city[]=13110"

STATE_FILE = "last_state.txt"


# =========================
# Selenium取得（クラウド対応）
# =========================
def fetch_html():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/chromium-browser"

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(TARGET_URL)
        time.sleep(5)
        html = driver.page_source
        return html

    finally:
        driver.quit()


# =========================
# 物件抽出
# =========================
def parse_properties(html):
    soup = BeautifulSoup(html, "html.parser")

    items = soup.select(".module_cassettes_property")

    results = []

    for item in items:
        name_tag = item.select_one(".rep_bukken-name")
        url_tag = item.select_one("a.rep_bukken-link")
        count_tag = item.select_one(".rep_bukken-count-room")

        if not name_tag:
            continue

        name = name_tag.text.strip()

        url = ""
        if url_tag and "href" in url_tag.attrs:
            url = "https://chintai.r6.ur-net.go.jp" + url_tag["href"]

        count = count_tag.text.strip() if count_tag else "0"

        results.append((name, url, count))

    return results


# =========================
# 状態管理
# =========================
def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    except:
        return set()


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(state))


# =========================
# Discord通知（メンション付き）
# =========================
def notify(name, url, count):
    content = (
        f"🚨 **UR空室変化検知** 🚨\n\n"
        f"🏠 {name}\n"
        f"🔑 空室数: {count}\n"
        f"🔗 {url}\n\n"
        f"<@{DISCORD_USER_ID}>"
    )

    requests.post(DISCORD_WEBHOOK_URL, json={"content": content})


# =========================
# メイン処理
# =========================
def main():
    print("ページ取得中...")

    html = fetch_html()
    props = parse_properties(html)

    last_state = load_state()
    current_state = set()

    for name, url, count in props:
        key = f"{name}|{count}"
        current_state.add(key)

        if key not in last_state:
            print("新規検知:", name)
            notify(name, url, count)

    save_state(current_state)

    print("完了")


if __name__ == "__main__":
    main()
