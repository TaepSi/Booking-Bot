"""
Слой работы с базой данных (SQLite через aiosqlite).

Таблицы:
  services     — услуги (название, цена, длительность)
  bookings     — записи клиентов
"""

import aiosqlite
from datetime import datetime

DB_PATH = "bookings.db"


async def init_db():
    """Создаёт таблицы, если они ещё не существуют."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                price       REAL    NOT NULL,
                duration    INTEGER NOT NULL  -- длительность в минутах
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                username    TEXT,
                full_name   TEXT,
                service_id  INTEGER NOT NULL,
                date        TEXT    NOT NULL,  -- YYYY-MM-DD
                time_slot   TEXT    NOT NULL,  -- HH:MM
                created_at  TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'active',  -- active / cancelled
                FOREIGN KEY (service_id) REFERENCES services(id)
            )
        """)
        await db.commit()


# ─── Услуги ────────────────────────────────────────────────────────────────────

async def add_service(name: str, price: float, duration: int) -> int:
    """Добавляет услугу и возвращает её id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO services (name, price, duration) VALUES (?, ?, ?)",
            (name, price, duration),
        )
        await db.commit()
        return cursor.lastrowid


async def get_services() -> list[dict]:
    """Возвращает список всех услуг."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM services ORDER BY name") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_service(service_id: int) -> dict | None:
    """Возвращает одну услугу по id или None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM services WHERE id = ?", (service_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_service(service_id: int):
    """Удаляет услугу по id."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM services WHERE id = ?", (service_id,))
        await db.commit()


# ─── Записи ────────────────────────────────────────────────────────────────────

async def create_booking(
    user_id: int,
    username: str | None,
    full_name: str,
    service_id: int,
    date: str,
    time_slot: str,
) -> int:
    """Создаёт новую запись и возвращает её id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO bookings
                (user_id, username, full_name, service_id, date, time_slot, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                full_name,
                service_id,
                date,
                time_slot,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_bookings(user_id: int) -> list[dict]:
    """Возвращает активные записи пользователя (с деталями услуги)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT b.*, s.name AS service_name, s.price, s.duration
            FROM   bookings b
            JOIN   services s ON s.id = b.service_id
            WHERE  b.user_id = ? AND b.status = 'active'
            ORDER  BY b.date, b.time_slot
            """,
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def cancel_booking(booking_id: int, user_id: int) -> bool:
    """
    Отменяет запись. Возвращает True если запись найдена и отменена,
    False если запись не принадлежит пользователю.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE bookings
            SET    status = 'cancelled'
            WHERE  id = ? AND user_id = ? AND status = 'active'
            """,
            (booking_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_booked_slots(service_id: int, date: str) -> set[str]:
    """Возвращает уже занятые слоты (HH:MM) для услуги на указанную дату."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT time_slot FROM bookings
            WHERE  service_id = ? AND date = ? AND status = 'active'
            """,
            (service_id, date),
        ) as cur:
            rows = await cur.fetchall()
            return {r[0] for r in rows}
