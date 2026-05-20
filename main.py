"""
Точка входа: запускает Flask keep-alive сервер и Telegram-бота одновременно.
"""

import asyncio
import threading
import logging
import os

from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from database import init_db
from handlers import client, admin

# ─── Логирование ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Переменные окружения ───────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]   # обязательно
ADMIN_ID  = int(os.environ["ADMIN_ID"])  # Telegram user_id администратора
PORT      = int(os.getenv("PORT", 10000))

# ─── Flask keep-alive (нужен для Render, чтобы сервис не засыпал) ──────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Bot is running ✅", 200

@flask_app.route("/health")
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

# ─── Aiogram ───────────────────────────────────────────────────────────────────
async def main():
    # Инициализация базы данных
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутеры
    dp.include_router(admin.router)
    dp.include_router(client.router)

    # Передаём ADMIN_ID в контекст через данные бота
    await dp.start_polling(bot, admin_id=ADMIN_ID)

if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    logger.info("Flask keep-alive запущен на порту %s", PORT)

    # Запускаем бота
    asyncio.run(main())
