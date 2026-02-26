import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, CHECK_INTERVAL_MINUTES
from database import init_db, is_tournament_known, add_tournament
from parser import fetch_tournaments
from handlers import router, notify_admin_new_tournament

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def check_new_tournaments(bot: Bot):
    """Periodic task: fetch tournaments and notify admin about new ones."""
    logger.info("Checking for new tournaments...")
    try:
        tournaments = fetch_tournaments()
    except Exception:
        logger.exception("Failed to fetch tournaments")
        return

    for t in tournaments:
        known = await is_tournament_known(t["key"])
        if not known:
            logger.info(f"New tournament found: {t['name']}")
            await add_tournament(
                cid=t["key"],
                name=t["name"],
                dates=t["dates"],
                image_url=t["image_url"],
                tournament_url=t["tournament_url"],
            )
            try:
                await notify_admin_new_tournament(bot, t)
            except Exception:
                logger.exception(f"Failed to notify admin about {t['name']}")


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Create .env file from .env.example")
        return

    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_new_tournaments,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        args=[bot],
    )
    scheduler.start()
    logger.info(f"Scheduler started (every {CHECK_INTERVAL_MINUTES} min)")

    # Run initial check on startup
    await check_new_tournaments(bot)

    logger.info("Bot started. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
