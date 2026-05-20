"""
Обработчики для клиентов:
  • Главное меню
  • Просмотр услуг
  • Запись (услуга → дата → слот → подтверждение)
  • Мои записи + отмена
  • Контакты
"""

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import (
    main_menu,
    services_inline,
    dates_inline,
    time_slots_inline,
    bookings_inline,
    fmt_booking,
)

router = Router()


# ─── FSM состояния записи ──────────────────────────────────────────────────────

class BookingFSM(StatesGroup):
    choosing_service = State()
    choosing_date    = State()
    choosing_time    = State()


# ─── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        f"👋 Привет, <b>{msg.from_user.full_name}</b>!\n\n"
        "Я помогу вам записаться на услуги. "
        "Выберите нужный пункт меню 👇\n\n"
        "———\n"
        "🔎 <i>Это демо-версия бота. Вы можете посмотреть, как работает "
        "админ-панель (команда /admin), но изменения не сохраняются. "
        "Для заказа персонального бота обратитесь к разработчику.</i>",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# ─── Услуги ───────────────────────────────────────────────────────────────────

@router.message(F.text == "📋 Услуги")
async def show_services(msg: Message):
    services = await db.get_services()
    if not services:
        await msg.answer("Пока услуг нет. Загляните позже!")
        return

    lines = ["<b>Наши услуги:</b>\n"]
    for s in services:
        lines.append(
            f"• <b>{s['name']}</b>\n"
            f"  💰 {s['price']:.0f} ₽  |  ⏱ {s['duration']} мин\n"
        )
    await msg.answer("\n".join(lines), parse_mode="HTML")


# ─── Контакты ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📞 Контакты")
async def show_contacts(msg: Message):
    await msg.answer(
        "📞 <b>Контакты</b>\n\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "📧 Email: info@example.com\n"
        "📍 Адрес: г. Москва, ул. Примерная, д. 1\n"
        "🕐 Режим работы: Пн–Сб 9:00–18:00",
        parse_mode="HTML",
    )


# ─── Запись: шаг 1 — выбор услуги ────────────────────────────────────────────

@router.message(F.text == "📅 Записаться")
async def start_booking(msg: Message, state: FSMContext):
    services = await db.get_services()
    if not services:
        await msg.answer(
            "К сожалению, сейчас нет доступных услуг. "
            "Пожалуйста, загляните позже."
        )
        return

    await state.set_state(BookingFSM.choosing_service)
    await msg.answer(
        "Выберите услугу:",
        reply_markup=services_inline(services, prefix="book"),
    )


@router.callback_query(BookingFSM.choosing_service, F.data.startswith("book:"))
async def booking_service_chosen(call: CallbackQuery, state: FSMContext):
    service_id = int(call.data.split(":")[1])
    service = await db.get_service(service_id)
    if not service:
        await call.answer("Услуга не найдена 😕", show_alert=True)
        return

    await state.update_data(service_id=service_id, service=service)
    await state.set_state(BookingFSM.choosing_date)

    await call.message.edit_text(
        f"Вы выбрали: <b>{service['name']}</b>\n"
        f"💰 {service['price']:.0f} ₽  |  ⏱ {service['duration']} мин\n\n"
        "Выберите дату:",
        reply_markup=dates_inline(),
        parse_mode="HTML",
    )
    await call.answer()


# ─── Запись: шаг 2 — выбор даты ──────────────────────────────────────────────

@router.callback_query(BookingFSM.choosing_date, F.data.startswith("date:"))
async def booking_date_chosen(call: CallbackQuery, state: FSMContext):
    date_str = call.data.split(":")[1]  # YYYY-MM-DD
    data = await state.get_data()
    service = data["service"]

    # Получаем занятые слоты
    booked = await db.get_booked_slots(data["service_id"], date_str)
    keyboard = time_slots_inline(service["duration"], booked)

    if keyboard is None:
        await call.answer(
            "На эту дату все слоты заняты. Выберите другую дату.",
            show_alert=True,
        )
        return

    await state.update_data(date=date_str)
    await state.set_state(BookingFSM.choosing_time)

    # Форматируем дату для отображения
    from datetime import date
    d = date.fromisoformat(date_str)
    ru_date = d.strftime("%d.%m.%Y")

    await call.message.edit_text(
        f"Дата: <b>{ru_date}</b>\n\n"
        "Выберите удобное время:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await call.answer()


# ─── Запись: шаг 3 — выбор времени → создание записи ─────────────────────────

@router.callback_query(BookingFSM.choosing_time, F.data.startswith("time:"))
async def booking_time_chosen(
    call: CallbackQuery, state: FSMContext, bot: Bot, admin_id: int
):
    time_slot = call.data.split(":")[1]
    data = await state.get_data()
    service = data["service"]
    date_str = data["date"]

    # Создаём запись в БД
    booking_id = await db.create_booking(
        user_id=call.from_user.id,
        username=call.from_user.username,
        full_name=call.from_user.full_name,
        service_id=data["service_id"],
        date=date_str,
        time_slot=time_slot,
    )

    await state.clear()

    # ── Уведомление клиенту ──
    from datetime import date as dt_date
    ru_date = dt_date.fromisoformat(date_str).strftime("%d.%m.%Y")

    await call.message.edit_text(
        "✅ <b>Вы успешно записаны!</b>\n\n"
        f"📌 {service['name']}\n"
        f"📅 {ru_date}  🕐 {time_slot}\n"
        f"💰 {service['price']:.0f} ₽\n\n"
        "Увидимся! Если нужно отменить — воспользуйтесь разделом «Мои записи».",
        parse_mode="HTML",
    )
    await call.answer("Запись создана ✅")

    # ── Уведомление администратору ──
    client_name = call.from_user.full_name
    client_link = (
        f"@{call.from_user.username}" if call.from_user.username
        else f"tg://user?id={call.from_user.id}"
    )
    try:
        await bot.send_message(
            admin_id,
            f"🔔 <b>Новая запись #{booking_id}</b>\n\n"
            f"📌 {service['name']}\n"
            f"📅 {ru_date}  🕐 {time_slot}\n"
            f"💰 {service['price']:.0f} ₽  |  ⏱ {service['duration']} мин\n\n"
            f"👤 Клиент: {client_name} ({client_link})",
            parse_mode="HTML",
        )
    except Exception:
        pass  # администратор мог заблокировать бота


# ─── Мои записи ───────────────────────────────────────────────────────────────

@router.message(F.text == "🗂 Мои записи")
async def my_bookings(msg: Message):
    bookings = await db.get_user_bookings(msg.from_user.id)
    if not bookings:
        await msg.answer(
            "У вас нет активных записей.\n"
            "Нажмите «📅 Записаться», чтобы создать новую."
        )
        return

    text_lines = ["<b>Ваши записи:</b>\n"]
    for b in bookings:
        text_lines.append(fmt_booking(b) + "\n")

    await msg.answer(
        "\n".join(text_lines) + "\nНажмите на запись, чтобы отменить её:",
        reply_markup=bookings_inline(bookings),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_booking(call: CallbackQuery):
    booking_id = int(call.data.split(":")[1])
    success = await db.cancel_booking(booking_id, call.from_user.id)

    if success:
        await call.answer("Запись отменена ✅", show_alert=True)
        # Обновляем список записей
        bookings = await db.get_user_bookings(call.from_user.id)
        if bookings:
            text_lines = ["<b>Ваши записи:</b>\n"]
            for b in bookings:
                text_lines.append(fmt_booking(b) + "\n")
            await call.message.edit_text(
                "\n".join(text_lines) + "\nНажмите на запись, чтобы отменить её:",
                reply_markup=bookings_inline(bookings),
                parse_mode="HTML",
            )
        else:
            await call.message.edit_text(
                "У вас больше нет активных записей."
            )
    else:
        await call.answer("Запись не найдена или уже отменена.", show_alert=True)
