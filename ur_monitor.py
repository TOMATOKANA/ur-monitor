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
MENTION_ID = f"<@{DISCORD_USER_ID}>" if DISCORD_USER_ID else ""

TARGET_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/"

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
# ブラウザ完全再現取得
# =========================

async def fetch_city(page, city_name, city_code):

    print(f"\n--- {city_name} ---")

    # ① ページ移動（通常ブラウザ相当）
    await page.goto(TARGET_URL, wait_until="domcontentloaded")

    # ② JS完全描画待ち（重要）
    await page.wait_for_load_state("networkidle")

    # ③ 地域チェック（UI依存）
    try:
        selector = f"input[value='{city_code}']"
        await page.check(selector)
    except:
        pass

    # ④ 検索ボタン（複数パターン対応）
    try:
        await page.click("text=検索")
    except:
        try:
            await page.click("button:has-text('検索')")
        except:
            pass

    # ⑤ JS結果待ち（最重要）
    try:
        await page.wait_for_selector(".module_cassettes_property", timeout=20000)
    except:
        print(f"{city_name}: DOM未生成")
        return {}

    # ⑥ 物件取得
    cards = await page.query_selector_all(".module_cassettes_property")

    print(f"{city_name} 件数:", len(cards))

    results = {}

    for card in cards:

        try:
            name_el = await card.query_selector(".rep_bukken-name")
            count_el = await card.query_selector(".rep_bukken-count-room")
            link_el = await card.query_selector("a")

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

            key = f"{city_name}:{name.strip()}"

            results[key] = {
                "count": count,
                "link": link
            }

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
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )

        page = await context.new_page()

        for city_name, city_code in CITIES.items():

            data = await fetch_city(page, city_name, city_code)

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

        await browser.close()

    save_cache(new)

# =========================
# 実行
# =========================

if __name__ == "__main__":
    asyncio.run(main())
