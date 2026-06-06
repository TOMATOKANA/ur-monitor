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

BASE_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/"

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
# ネットワーク監視コア
# =========================

async def fetch_city(page, city_name, city_code):

    print(f"\n--- {city_name} ---")

    captured = []

    # =========================
    # レスポンス監視フック
    # =========================
    def handle_response(response):
        try:
            url = response.url
            ct = response.headers.get("content-type", "")

            # JSONっぽい通信だけ拾う
            if "json" in ct or "api" in url or "search" in url:
                captured.append(response)
        except:
            pass

    page.on("response", handle_response)

    # =========================
    # ページ遷移（結果ページ直）
    # =========================
    url = BASE_URL + f"?city%5B%5D={city_code}"

    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)

    # =========================
    # ネットワーク待機
    # =========================
    await page.wait_for_timeout(3000)

    data = None

    # =========================
    # JSONレスポンス探索
    # =========================
    for res in captured:

        try:
            body = await res.json()

            # URっぽい構造を柔軟に吸収
            if isinstance(body, dict):

                if "data" in body:
                    data = body["data"]
                    break

                if "properties" in body:
                    data = body["properties"]
                    break

                if "result" in body:
                    data = body["result"]
                    break

        except:
            continue

    # =========================
    # fallback（どうしても取れない場合）
    # =========================
    if not data:
        print(f"{city_name}: JSON未取得 → DOMフォールバック")

        selectors = [
            ".module_cassettes_property",
            ".cassetteitem",
            "article"
        ]

        for sel in selectors:
            try:
                await page.wait_for_selector(sel, timeout=10000)
                cards = await page.query_selector_all(sel)

                results = {}

                for card in cards:
                    try:
                        name_el = await card.query_selector("h2")
                        count_el = await card.query_selector(".rep_bukken-count-room")

                        name = await name_el.inner_text() if name_el else "不明"
                        count_text = await count_el.inner_text() if count_el else "0"

                        count = int("".join([c for c in count_text if c.isdigit()] or "0"))

                        key = f"{city_name}:{name.strip()}"

                        results[key] = {"count": count, "link": ""}

                    except:
                        continue

                return results

            except:
                continue

        print(f"{city_name}: 完全失敗")
        return {}

    # =========================
    # JSON解析
    # =========================

    results = {}

    try:
        for item in data:

            if not isinstance(item, dict):
                continue

            name = item.get("name") or item.get("bukkenName") or "不明"
            count = item.get("vacancyCount") or item.get("count") or 0
            link = item.get("detailUrl") or ""

            if link and not link.startswith("http"):
                link = "https://chintai.r6.ur-net.go.jp" + link

            key = f"{city_name}:{name}"

            results[key] = {
                "count": int(count),
                "link": link
            }

    except:
        print(f"{city_name}: JSON解析失敗")

    print(f"{city_name} 件数:", len(results))

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
                        f"{v.get('link','')}"
                    )

        await browser.close()

    save_cache(new)

# =========================
# 実行
# =========================

if __name__ == "__main__":
    asyncio.run(main())
