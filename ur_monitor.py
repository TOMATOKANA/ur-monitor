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

BASE_URL = "https://chintai.r6.ur-net.go.jp/"

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
# フロー（完全デバッグ版）
# =========================

async def fetch_city(page, city_name, city_code):

    print(f"\n--- {city_name} ---")

    try:
        # ① トップページ
        print("ページを開く...")
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        # スクショ（重要）
        await page.screenshot(path=f"debug_{city_name}_1_top.png", full_page=True)

        # HTML保存
        with open(f"debug_{city_name}_1_top.html", "w", encoding="utf-8") as f:
            f.write(await page.content())

        print("地域操作開始...")

        # ② とりあえずクリック探索（UI不明対策）
        clicked = False

        try:
            # checkbox想定
            await page.check(f"input[value='{city_code}']")
            clicked = True
        except:
            pass

        if not clicked:
            try:
                # テキストクリック
                await page.click(f"text={city_name}")
                clicked = True
            except:
                pass

        if not clicked:
            try:
                # labelクリック
                await page.click(f"label:has-text('{city_name}')")
                clicked = True
            except:
                pass

        if not clicked:
            print(f"{city_name}: 地域選択失敗")
            await page.screenshot(path=f"debug_{city_name}_fail.png", full_page=True)
            return []

        print("検索実行...")

        # ③ 検索ボタン（複数パターン）
        searched = False

        for sel in ["text=検索", "text=この条件で検索", "button[type='submit']"]:
            try:
                await page.click(sel)
                searched = True
                break
            except:
                continue

        if not searched:
            print(f"{city_name}: 検索ボタン失敗")
            await page.screenshot(path=f"debug_{city_name}_search_fail.png", full_page=True)
            return []

        print("結果待機中...")
        await page.wait_for_timeout(8000)

        # =========================
        # 結果保存
        # =========================

        await page.screenshot(path=f"debug_{city_name}_result.png", full_page=True)

        with open(f"debug_{city_name}_result.html", "w", encoding="utf-8") as f:
            f.write(await page.content())

        # =========================
        # DOM確認
        # =========================

        html = await page.content()

        if "404" in html:
            print(f"{city_name}: 404検出")
            return []

        selectors = [
            ".module_cassettes_property",
            ".cassetteitem",
            "article",
            ".property"
        ]

        cards = []

        for sel in selectors:
            try:
                cards = await page.query_selector_all(sel)
                if cards:
                    print(f"{city_name}: selector hit -> {sel}")
                    break
            except:
                continue

        if not cards:
            print(f"{city_name}: DOMなし")
            return []

        print(f"{city_name}: 取得成功 {len(cards)}件")

        return [{"key": f"{city_name}:dummy", "count": len(cards)}]

    except Exception as e:
        print(f"{city_name}: フロー例外 -> {e}")
        await page.screenshot(path=f"debug_{city_name}_exception.png", full_page=True)
        return []

# =========================
# メイン
# =========================

async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()

        for city_name, city_code in CITIES.items():
            await fetch_city(page, city_name, city_code)

        await browser.close()

# =========================
# 実行
# =========================

if __name__ == "__main__":
    asyncio.run(main())
