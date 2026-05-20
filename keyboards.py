"""
Общие клавиатуры и вспомогательные функции.
"""

from datetime import datetime, timedelta
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ─── Главное меню ──────────────────────────────────────────────────────────────

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Услуги"),    KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="🗂 Мои записи"), KeyboardButton(text="📞 Контакты")],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить услугу"), KeyboardButton(text="🗑 Удалить услугу")],
            [KeyboardButton(text="📋 Все услуги"),      KeyboardButton(text="🔙 Главное меню")],
        ],
        resize_keyboard=True,
    )


# ─── Inline-клавиатуры ─────────────────────────────────────────────────────────

def services_inline(services: list[dict], prefix: str = "book") -> InlineKeyboardMarkup:
    """
    Строит inline-меню из списка услуг.
    prefix="book"   → для записи клиента
    prefix="del"    → для удаления администратором
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{s['name']} — {s['price']:.0f} ₽ ({s['duration']} мин)",
                callback_data=f"{prefix}:{s['id']}",
            )
        ]
        for s in services
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dates_inline(days_ahead: int = 14) -> InlineKeyboardMarkup:
    """Строит inline-меню дат на ближайшие days_ahead дней (исключая воскресенье)."""
    buttons = []
    today = datetime.now().date()
    for i in range(days_ahead):
        day = today + timedelta(days=i)
        if day.weekday() == 6:  # пропускаем воскресенье
            continue
        label = day.strftime("%d.%m.%Y") + (
            " (сегодня)" if i == 0 else
            " (завтра)"  if i == 1 else
            ""
        )
        buttons.append(
            [InlineKeyboardButton(text=label, callback_data=f"date:{day.isoformat()}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_slots_inline(
    duration: int, booked: set[str]
) -> InlineKeyboardMarkup | None:
    """
    Генерирует доступные временные слоты с 9:00 до 18:00
    с шагом duration минут. Уже занятые слоты исключаются.
    Возвращает None, если свободных слотов нет.
    """
    start_h, start_m = 9, 0
    end_h, end_m     = 18, 0

    current = datetime.now().replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end     = datetime.now().replace(hour=end_h,   minute=end_m,   second=0, microsecond=0)

    buttons = []
    while current < end:
        slot = current.strftime("%H:%M")
        if slot not in booked:
            buttons.append(
                [InlineKeyboardButton(text=slot, callback_data=f"time:{slot}")]
            )
        current += timedelta(minutes=duration)

    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def bookings_inline(bookings: list[dict]) -> InlineKeyboardMarkup:
    """Inline-меню для отмены записей клиентом."""
    buttons = [
        [
            InlineKeyboardButton(
                text=(
                    f"❌ {b['service_name']} — "
                    f"{b['date']} {b['time_slot']}"
                ),
                callback_data=f"cancel:{b['id']}",
            )
        ]
        for b in bookings
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── Форматирование ────────────────────────────────────────────────────────────

def fmt_booking(b: dict, include_client: bool = False) -> str:
    """Красиво форматирует запись для отображения в сообщении."""
    lines = [
        f"📌 <b>{b['service_name']}</b>",
        f"📅 {b['date']}  🕐 {b['time_slot']}",
        f"💰 {b['price']:.0f} ₽  ⏱ {b['duration']} мин",
    ]
    if include_client:
        client_line = f"👤 {b['full_name']}"
        if b.get("username"):
            client_line += f" (@{b['username']})"
        lines.append(client_line)
    return "\n".join(lines)
