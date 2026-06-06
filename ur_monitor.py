import requests
from bs4 import BeautifulSoup

URL = "https://chintai.r6.ur-net.go.jp/chintai/kanto/tokyo/search/result/?city[]=13110"

def fetch():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    for card in soup.select(".module_cassettes_property"):
        name_tag = card.select_one(".rep_bukken-name")
        count_tag = card.select_one(".rep_bukken-count-room")
        link_tag = card.select_one("a.rep_bukken-link")

        if not name_tag:
            continue

        name = name_tag.text.strip()

        try:
            count = int(count_tag.text.strip())
        except:
            count = 0

        link = ""
        if link_tag and link_tag.get("href"):
            link = "https://chintai.r6.ur-net.go.jp" + link_tag["href"]

        results.append((name, count, link))

    return results


def main():
    data = fetch()

    for name, count, link in data:
        if count > 0:
            print(f"🆕 {name}（{count}件）{link}")


if __name__ == "__main__":
    main()
