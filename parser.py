import re
from datetime import datetime, date

import requests
from bs4 import BeautifulSoup
from config import PARSER_URL, BASE_URL


def fetch_tournaments() -> list[dict]:
    """Fetch list of tournaments from padelteams.pt organizer page."""
    response = requests.get(PARSER_URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    tournaments = []
    for link_tag in soup.select("a[href*='/info/competition?k=']"):
        href = link_tag.get("href", "")
        # Extract encoded competition key
        match = re.search(r"k=([A-Za-z0-9%=]+)", href)
        if not match:
            continue
        key = match.group(1)

        card = link_tag

        # Tournament name
        name_el = card.select_one("div.text-dark.bold")
        name = name_el.get_text(strip=True) if name_el else "Unknown"

        # Dates
        date_spans = card.select("span.px2.bold")
        if len(date_spans) >= 2:
            dates = f"{date_spans[0].get_text(strip=True)} / {date_spans[1].get_text(strip=True)}"
        elif len(date_spans) == 1:
            dates = date_spans[0].get_text(strip=True)
        else:
            dates = ""

        # Image URL (thumbnail)
        img_el = card.select_one("img.cover-image-mini")
        image_url = ""
        if img_el:
            src = img_el.get("src", "")
            if src:
                # Convert thumbnail to full-size: remove _t before extension
                full_src = re.sub(r"_t\.(jpeg|jpg|png|webp)$", r".\1", src)
                image_url = BASE_URL + full_src if full_src.startswith("/") else full_src

        tournament_url = BASE_URL + href if href.startswith("/") else href

        # Filter: only future tournaments (last date >= today)
        last_date_str = dates.split("/")[-1].strip()
        try:
            last_date = datetime.strptime(last_date_str, "%d-%m-%Y").date()
        except ValueError:
            last_date = None

        if last_date and last_date < date.today():
            continue

        tournaments.append({
            "key": key,
            "name": name,
            "dates": dates,
            "image_url": image_url,
            "tournament_url": tournament_url,
        })

    return tournaments


if __name__ == "__main__":
    results = fetch_tournaments()
    for t in results:
        print(f"{t['name']} | {t['dates']} | {t['tournament_url']}")
        print(f"  Image: {t['image_url']}")
        print()
