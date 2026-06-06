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

BASE_URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/"

# =========================
# 対象地域（10エリア）
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
    return BASE_URL + "?" + "&".join(
        [f"city%5B%5D={code}" for code in CITIES.values()]
    )

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
# 取得処理（安定版）
# =========================

async def fetch_properties():

    results = {}

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()

        url = build_url()

        print("ページ取得中...")
        print("URL:", url)

        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # ★重要：JS描画待ち（UR対策）
        await page.wait_for_load_state("networkidle")

        # ★重要：DOM出現待ち（2段階）
        try:
            await page.wait_for_selector(".module_cassettes_property", timeout=20000)
        except:
            print("⚠ DOM取得失敗（HTML保存）")

            html = await page.content()
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(html)

            await browser.close()
            return {}

        cards = await page.query_selector_all(".module_cassettes_property")

        print("取得完了")
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

                results[name.strip()] = {
                    "count": count,
                    "link": link
                }

            except:
                continue

        await browser.close()

    return results

# =========================
# メイン処理
# =========================

async def main():

    old = load_cache()
    new = await fetch_properties()

    print("\n取得結果")
    print("=" * 50)

    for name, data in new.items():

        count = data["count"]
        link = data["link"]

        print(name, count)

        old_count = old.get(name, {}).get("count", 0)

        if count > old_count:

            notify(
                f"{MENTION_ID} 🆕空室増加\n"
                f"{name}\n"
                f"{old_count} → {count}\n"
                f"{link}"
            )

    save_cache(new)

# =========================
# 実行
# =========================

if __name__ == "__main__":
    asyncio.run(main())
