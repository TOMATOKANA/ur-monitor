import os
import json
import asyncio
import requests
from playwright.async_api import async_playwright

# =========================
# 設定
# =========================

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
DISCORD_USER_ID = os.environ.get("DISCORD_USER_ID")
MENTION = f"<@{DISCORD_USER_ID}>" if DISCORD_USER_ID else ""

BASE_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city%5B%5D="

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
# 通知
# =========================

def notify(msg):
    if not DISCORD_WEBHOOK:
        print(msg)
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except:
        pass

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
# データ正規化
# =========================

def normalize(name, count, link, city):
    if not name:
        name = "不明"

    try:
        count = int(str(count))
    except:
        count = 0

    return {
        "key": f"{city}:{name.strip()}",
        "name": name.strip(),
        "count": count,
        "link": link or ""
    }

# =========================
# 取得 + HTMLデバッグ
# =========================

async def fetch_city(page, city_name, city_code):

    url = BASE_URL + city_code

    print(f"\n--- {city_name} ---")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
    except:
        return []

    # =========================
    # HTMLデバッグ保存（重要）
    # =========================
    try:
        html = await page.content()
        with open(f"debug_{city_name}.html", "w", encoding="utf-8") as f:
            f.write(html)
    except:
        pass

    # =========================
    # セレクタ探索
    # =========================

    selectors = [
        ".module_cassettes_property",
        ".cassetteitem",
        "article"
    ]

    cards = []

    for sel in selectors:
        try:
            cards = await page.query_selector_all(sel)
            if cards:
                break
        except:
            continue

    if not cards:
        print(f"{city_name}: DOMなし")
        return []

    results = []

    for card in cards:
        try:
            name_el = await card.query_selector("h2")
            count_el = await card.query_selector(".rep_bukken-count-room")

            name = await name_el.inner_text() if name_el else None
            count = await count_el.inner_text() if count_el else "0"

            a = await card.query_selector("a")
            link = ""

            if a:
                href = await a.get_attribute("href")
                if href:
                    link = "https://chintai.r6.ur-net.go.jp" + href

            results.append(normalize(name, count, link, city_name))

        except:
            continue

    return results

# =========================
# メイン
# =========================

async def main():

    old = load_cache()
    new = {}

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()

        for city_name, city_code in CITIES.items():

            items = await fetch_city(page, city_name, city_code)

            if not items:
                continue

            for item in items:

                key = item["key"]
                new[key] = item

                old_count = old.get(key, {}).get("count", 0)

                if item["count"] > old_count:

                    notify(
                        f"{MENTION} 🆕空室増加\n"
                        f"{key}\n"
                        f"{old_count} → {item['count']}\n"
                        f"{item['link']}"
                    )

        await browser.close()

    save_cache(new)

# =========================
# 実行
# =========================

if __name__ == "__main__":
    asyncio.run(main())
