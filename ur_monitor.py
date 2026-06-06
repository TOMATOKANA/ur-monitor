import json
import asyncio
from playwright.async_api import async_playwright
import requests
import os

# =========================
# 設定
# =========================

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")DISCORD_USER_ID
DISCORD_WEBHOOK = os.environ.get("DISCORD_USER_ID")

BASE_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?"

# =========================
# 監視対象（指定10地域）
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
# URL生成
# =========================
def build_url():
    return BASE_URL + "&".join(
        [f"city%5B%5D={code}" for code in CITIES.values()]
    )


# =========================
# Discord通知
# =========================
def notify(message: str):
    if not DISCORD_WEBHOOK:
        print("Webhook未設定")
        return

    requests.post(DISCORD_WEBHOOK, json={"content": message})


# =========================
# キャッシュ管理
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
# Playwright取得
# =========================
async def fetch_properties():

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()

        url = build_url()

        print("ページ取得中...")
        await page.goto(url, wait_until="networkidle", timeout=60000)

        print("取得完了")

        cards = await page.query_selector_all(".module_cassettes_property")

        print("物件数:", len(cards))

        for card in cards:

            try:
                name_el = await card.query_selector(".rep_bukken-name")
                count_el = await card.query_selector(".rep_bukken-count-room")
                link_el = await card.query_selector("a.rep_bukken-link")

                name = await name_el.inner_text() if name_el else "不明"

                count_text = await count_el.inner_text() if count_el else "0"
                try:
                    count = int(count_text)
                except:
                    count = 0

                link = ""
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        link = "https://chintai.r6.ur-net.go.jp" + href

                results.append({
                    "name": name.strip(),
                    "count": count,
                    "link": link
                })

            except:
                continue

        await browser.close()

    return results


# =========================
# メイン処理
# =========================
async def main():

    old_cache = load_cache()
    new_cache = {}

    data = await fetch_properties()

    print("\n取得結果")
    print("=" * 50)

    for item in data:

        name = item["name"]
        count = item["count"]
        link = item["link"]

        print(f"{name} / {count}")

        new_cache[name] = count

        old_count = old_cache.get(name, 0)

        # 空室増加のみ通知
        if count > old_count:

            msg = (
                f"{MENTION_ID} 🆕空室増加検知\n"
                f"物件: {name}\n"
                f"前: {old_count} → 現在: {count}\n"
                f"{link}"
            )

            notify(msg)

    save_cache(new_cache)


if __name__ == "__main__":
    asyncio.run(main())
