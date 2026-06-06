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

# =========================
# UR対象地域
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

BASE_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/"

# =========================
# Discord通知
# =========================

def notify(msg):
    if not DISCORD_WEBHOOK:
        print("Webhook未設定")
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
# APIレスポンス取得（XHR監視）
# =========================

async def fetch_city_api(page, city_name, city_code):

    url = BASE_URL + f"?city%5B%5D={city_code}"

    print(f"\n--- {city_name} ---")
    print(url)

    data_container = {}

    # ネットワークレスポンス監視
    def handle_response(response):
        try:
            if "application/json" in response.headers.get("content-type", ""):
                data_container["json"] = asyncio.create_task(response.json())
        except:
            pass

    page.on("response", handle_response)

    await page.goto(url, wait_until="domcontentloaded")

    await page.wait_for_timeout(5000)

    # JSON取得待ち
    json_data = None
    if "json" in data_container:
        try:
            json_data = await data_container["json"]
        except:
            json_data = None

    # fallback（DOM）
    if not json_data:
        print(f"{city_name}: APIなし → DOMフォールバック")

        await page.wait_for_selector(".module_cassettes_property", timeout=15000)
        cards = await page.query_selector_all(".module_cassettes_property")

        results = {}

        for card in cards:
            try:
                name_el = await card.query_selector(".rep_bukken-name")
                count_el = await card.query_selector(".rep_bukken-count-room")

                name = await name_el.inner_text() if name_el else "不明"
                count_text = await count_el.inner_text() if count_el else "0"

                try:
                    count = int(count_text)
                except:
                    count = 0

                results[f"{city_name}:{name.strip()}"] = {
                    "count": count
                }

            except:
                continue

        return results

    # JSON構造解析（サイト依存）
    results = {}

    try:
        # ここはUR構造変化に対応できるよう安全処理
        items = json_data.get("properties") or json_data.get("data") or []

        for item in items:
            name = item.get("name", "不明")
            count = item.get("vacancyCount", 0)

            results[f"{city_name}:{name}"] = {
                "count": int(count)
            }

    except:
        print(f"{city_name}: JSON解析失敗")

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

            data = await fetch_city_api(page, city_name, city_code)

            for k, v in data.items():

                new[k] = v

                old_count = old.get(k, {}).get("count", 0)

                if v["count"] > old_count:

                    notify(
                        f"{MENTION_ID} 🆕空室増加検知\n"
                        f"{k}\n"
                        f"{old_count} → {v['count']}"
                    )

        await browser.close()

    save_cache(new)

# =========================
# 実行
# =========================

if __name__ == "__main__":
    asyncio.run(main())
