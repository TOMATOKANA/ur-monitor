import os
import json
import requests

STATE_FILE = "state.json"

# =========================
# Discord設定（GitHub Secrets）
# =========================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_USER_ID = os.getenv("DISCORD_USER_ID")


# =========================
# 状態管理
# =========================
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


# =========================
# Discord送信（メンション付き）
# =========================
def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("Webhook未設定")
        return

    payload = {
        "content": f"<@{DISCORD_USER_ID}> {message}"
    }

    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print("Discord status:", r.status_code, r.text)
    except Exception as e:
        print("Discord送信エラー:", e)


# =========================
# UR取得（ここはあなたのSeleniumに置き換え済み想定）
# =========================
def fetch_data():
    """
    ここにSelenium or requestsで取得した結果を返す

    例：
    {
        "恵比寿ビュータワー": 2,
        "中目黒ゲートタウンハイツ": 1
    }
    """

    # ★テスト用（動作確認が終わったら削除OK）
    return {
        "テスト物件A": 1,
        "テスト物件B": 2
    }


# =========================
# 差分検知（取りこぼしゼロ版）
# =========================
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


# =========================
# メイン処理
# =========================
def main():
    print("UR Monitor start")

    current_data = fetch_data()

    print("取得データ:", current_data)

    changes = detect_changes(current_data)

    print("検知結果:", changes)

    if changes:
        for msg in changes:
            print("送信:", msg)
            send_discord(msg)
    else:
        print("変化なし")


if __name__ == "__main__":
    main()
