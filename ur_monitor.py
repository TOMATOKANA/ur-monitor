import os
import json
import requests

STATE_FILE = "state.json"

# ===== Discord設定 =====
DISCORD_WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1512593894292979763/rDqQiE18d0aBdLpZqOc9P3Z_prepaJz_SG1BU-_6S7oL-imeGooK5YvIinxJ5r1GGiYD")
DISCORD_USER_ID = os.getenv("329597244204515328")  # メンション用


# ===== 状態管理 =====
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ===== Discord通知（メンション付き）=====
def notify_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("Webhook未設定")
        return

    payload = {
        "content": f"<@{DISCORD_USER_ID}> {message}"
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print("Discord送信エラー:", e)


# ===== 差分検知（取りこぼしゼロ版）=====
def detect_changes(current_data):
    old_data = load_state()
    notifications = []

    # 新規・増加・復活
    for name, current_count in current_data.items():
        old_count = old_data.get(name)

        if old_count is None:
            if current_count > 0:
                notifications.append(f"🆕新規空室: {name}（{current_count}件）")

        else:
            if old_count == 0 and current_count > 0:
                notifications.append(f"🔔復活: {name}（{current_count}件）")

            elif current_count > old_count:
                notifications.append(
                    f"📈増加: {name}（{old_count} → {current_count}件）"
                )

    # 取得漏れ検知
    for name in old_data:
        if name not in current_data:
            notifications.append(f"⚠️取得漏れ可能性: {name}")

    save_state(current_data)
    return notifications


# ===== Seleniumの代わり（ここはあなたの取得関数を接続）=====
def fetch_data():
    """
    ここにSelenium処理を入れる
    return例:
    {
        "恵比寿ビュータワー": 2,
        "中目黒ゲートタウンハイツ": 0
    }
    """
    return {}


# ===== メイン =====
def main():
    print("UR Monitor start")

    current = fetch_data()

    changes = detect_changes(current)

    if changes:
        for msg in changes:
            print(msg)
            notify_discord(msg)
    else:
        print("変化なし")


if __name__ == "__main__":
    main()
