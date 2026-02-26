import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cid TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                dates TEXT NOT NULL,
                image_url TEXT,
                tournament_url TEXT,
                source TEXT DEFAULT 'padelteams',
                location TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def is_tournament_known(cid: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM tournaments WHERE cid = ?", (cid,)
        )
        row = await cursor.fetchone()
        return row is not None


async def add_tournament(cid: str, name: str, dates: str, image_url: str, tournament_url: str, source: str = "padelteams", location: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO tournaments (cid, name, dates, image_url, tournament_url, source, location) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, name, dates, image_url, tournament_url, source, location),
        )
        await db.commit()


async def get_tournament_by_cid(cid: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tournaments WHERE cid = ?", (cid,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def mark_published(cid: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tournaments SET status = 'published' WHERE cid = ?", (cid,)
        )
        await db.commit()
