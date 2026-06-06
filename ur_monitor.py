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

BASE = "https://chintai.r6.ur-net.go.jp/chintai/"

# =========================
# 対象地域
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
# 通知
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
# フルフロー取得
# =========================

async def fetch_city(page, city_name, city_code):

    print(f"\n--- {city_name} ---")

    # ① トップページへ（重要）
    await page.goto(BASE, wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # ② 地域選択画面へ遷移
    try:
        await page.goto(
            f"https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/?city%5B%5D={city_code}",
            wait_until="domcontentloaded"
        )
    except:
        print("検索ページ遷移失敗")
        return {}

    await page.wait_for_timeout(3000)

    # ③ 念のためJS安定待機
    await page.wait_for_load_state("networkidle")

    # ④ 検索結果待機（ここが重要）
    selectors = [
        ".module_cassettes_property",
        ".cassetteitem",
        "article"
    ]

    cards = []

    for sel in selectors:
        try:
            await page.wait_for_selector(sel, timeout=20000)
            cards = await page.query_selector_all(sel)
            if cards:
                break
        except:
            continue

    if not cards:
        print("DOM未生成（フロー未発火）")
        html = await page.content()
        with open(f"debug_{city_code}.html", "w", encoding="utf-8") as f:
            f.write(html)
        return {}

    print("取得件数:", len(cards))

    results = {}

    # ⑤ データ抽出
    for card in cards:

        try:
            name_el = await card.query_selector(".rep_bukken-name")
            if not name_el:
                name_el = await card.query_selector("h2")

            count_el = await card.query_selector(".rep_bukken-count-room")

            name = await name_el.inner_text() if name_el else "不明"
            count_text = await count_el.inner_text() if count_el else "0"

            try:
                count = int("".join([c for c in count_text if c.isdigit()]))
            except:
                count = 0

            link = ""
            a = await card.query_selector("a")
            if a:
                href = await a.get_attribute("href")
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
            args=["--no-sandbox"]
        )

        page = await browser.new_page()

        for city_name, city_code in CITIES.items():

            data = await fetch_city(page, city_name, city_code)

            for k, v in data.items():

                new[k] = v

                old_count = old.get(k, {}).get("count", 0)

                if v["count"] > old_count:

                    notify(
                        f"{MENTION} 🆕空室増加\n"
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
