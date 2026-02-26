import io
import re
from datetime import datetime

import requests
from aiogram import Bot
from aiogram.types import BufferedInputFile

from config import GROUP_CHAT_ID, TOPIC_ID, VENUES_FILE

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def load_venues() -> list[dict]:
    """Load venues from venues.txt file."""
    venues = []
    with open(VENUES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                venues.append({
                    "name": parts[0].strip(),
                    "url": parts[1].strip(),
                })
    return venues


def format_dates_russian(dates_str: str) -> str:
    """Convert dates like '21-03-2026 / 22-03-2026' to Russian format."""
    dates_str = dates_str.strip()
    parts = [d.strip() for d in dates_str.split("/")]

    parsed = []
    for part in parts:
        try:
            parsed.append(datetime.strptime(part, "%d-%m-%Y"))
        except ValueError:
            return dates_str

    if len(parsed) == 1:
        d = parsed[0]
        return f"{d.day} {MONTHS_RU[d.month]} {d.year}"

    if len(parsed) == 2:
        d1, d2 = parsed
        if d1 == d2:
            return f"{d1.day} {MONTHS_RU[d1.month]} {d1.year}"
        if d1.month == d2.month and d1.year == d2.year:
            return f"{d1.day}-{d2.day} {MONTHS_RU[d1.month]} {d1.year}"
        if d1.year == d2.year:
            return f"{d1.day} {MONTHS_RU[d1.month]} - {d2.day} {MONTHS_RU[d2.month]} {d2.year}"
        return f"{d1.day} {MONTHS_RU[d1.month]} {d1.year} - {d2.day} {MONTHS_RU[d2.month]} {d2.year}"

    return dates_str


def format_post(tournament: dict, venue: dict, description: str) -> str:
    """Format the post caption in HTML."""
    name = tournament["name"]
    url = tournament["tournament_url"]
    dates_ru = format_dates_russian(tournament["dates"])

    source = tournament.get("source", "padelteams")
    if source == "tiepadel":
        organizer = "Federação Portuguesa de Padel"
        tour_type = "Federation"
    else:
        organizer = "Padel Players"
        tour_type = "Social"

    lines = [
        f'<a href="{url}">{name}</a>',
        f"📅 {dates_ru}",
        f'📍 <a href="{venue["url"]}">{venue["name"]}</a>',
        f"<b>Организатор:</b> {organizer}",
        f"<b>Тип турнира:</b> {tour_type}",
    ]
    if description:
        lines.append("")
        lines.append(description)

    return "\n".join(lines)


def download_image(image_url: str) -> bytes | None:
    """Download tournament image."""
    try:
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


async def publish_to_group(bot: Bot, tournament: dict, venue: dict, description: str):
    """Publish formatted post with photo to Telegram group topic."""
    caption = format_post(tournament, venue, description)
    image_data = download_image(tournament["image_url"])

    if image_data:
        ext = tournament["image_url"].rsplit(".", 1)[-1] if "." in tournament["image_url"] else "jpeg"
        photo = BufferedInputFile(image_data, filename=f"tournament.{ext}")
        await bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=TOPIC_ID if TOPIC_ID else None,
            photo=photo,
            caption=caption,
            parse_mode="HTML",
        )
    else:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=TOPIC_ID if TOPIC_ID else None,
            text=caption,
            parse_mode="HTML",
        )
