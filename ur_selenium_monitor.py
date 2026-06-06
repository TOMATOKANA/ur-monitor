import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =========================
# 設定
# =========================
TARGET_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city[]=13110"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1512593894292979763/rDqQiE18d0aBdLpZqOc9P3Z_prepaJz_SG1BU-_6S7oL-imeGooK5YvIinxJ5r1GGiYD"
MENTION_ID = "<@329597244204515328>"  # 自分メンション

CHECK_INTERVAL = 300  # 5分

# =========================
# Selenium設定
# =========================
def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


# =========================
# 物件取得
# =========================
def fetch_properties(driver):
    print("ページ取得中...")
    driver.get(TARGET_URL)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".rep_bukken-name")))

    properties = []

    cards = driver.find_elements(By.CSS_SELECTOR, ".module_cassettes_property")

    for card in cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, ".rep_bukken-name").text.strip()
        except:
            continue

        try:
            count_text = card.find_element(By.CSS_SELECTOR, ".rep_bukken-count-room").text.strip()
            count = int(count_text)
        except:
            count = 0

        try:
            link = card.find_element(By.CSS_SELECTOR, "a.rep_bukken-link").get_attribute("href")
        except:
            link = ""

        properties.append({
            "name": name,
            "count": count,
            "link": link
        })

    return properties


# =========================
# 差分検出
# =========================
def diff_properties(old, new):
    old_map = {p["name"]: p["count"] for p in old}
    new_map = {p["name"]: p["count"] for p in new}

    alerts = []

    for name, count in new_map.items():
        if name not in old_map:
            alerts.append((name, count, "NEW"))
        elif count > old_map[name]:
            alerts.append((name, count, "INCREASE"))

    return alerts


# =========================
# Discord通知
# =========================
def send_discord(alerts):
    if not alerts:
        return

    lines = []
    for name, count, mode in alerts:
        if mode == "NEW":
            lines.append(f"{MENTION_ID} 🆕新規空室: {name}（{count}件）")
        else:
            lines.append(f"{MENTION_ID} 📈空室増加: {name}（{count}件）")

    payload = {
        "content": "\n".join(lines)
    }

    requests.post(DISCORD_WEBHOOK_URL, json=payload)


# =========================
# メインループ
# =========================
def main():
    driver = create_driver()

    print("初回取得...")
    old_data = fetch_properties(driver)
    print("初回完了")

    while True:
        try:
            time.sleep(CHECK_INTERVAL)

            new_data = fetch_properties(driver)
            alerts = diff_properties(old_data, new_data)

            if alerts:
                send_discord(alerts)
                print("通知送信:", alerts)
            else:
                print("変化なし")

            old_data = new_data

        except Exception as e:
            print("エラー:", e)


if __name__ == "__main__":
    main()
