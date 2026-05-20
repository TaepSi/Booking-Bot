"""
Обработчики админ-панели — ДЕМО-режим.

Доступна любому пользователю (/admin), но изменения в базу НЕ записываются:
  • «Добавить услугу» — проходит все шаги FSM, показывает успех, ничего не сохраняет.
  • «Удалить услугу»  — показывает реальный список, даёт выбрать, показывает успех, ничего не удаляет.
  • «Все услуги»      — показывает реальные данные из базы (только чтение).
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import admin_menu, main_menu, services_inline

router = Router()
# Фильтр IsAdmin удалён — панель доступна всем в демо-режиме.


# ─── FSM состояния добавления услуги ──────────────────────────────────────────

class AddServiceFSM(StatesGroup):
    waiting_name     = State()
    waiting_price    = State()
    waiting_duration = State()


# ─── Вход в админ-панель ──────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "🛠 <b>Админ-панель</b> <i>(демо-режим)</i>\n\n"
        "⚠️ Изменения здесь <b>не сохраняются</b> — это демонстрация интерфейса.\n\n"
        "Выберите действие:",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


@router.message(F.text == "🔙 Главное меню")
async def back_to_main(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Главное меню", reply_markup=main_menu())


# ─── Просмотр услуг — реальные данные из базы (только чтение) ─────────────────

@router.message(F.text == "📋 Все услуги")
async def admin_list_services(msg: Message):
    services = await db.get_services()
    if not services:
        await msg.answer("Услуг пока нет.")
        return

    lines = ["<b>Все услуги:</b>\n"]
    for s in services:
        lines.append(
            f"#{s['id']} <b>{s['name']}</b>\n"
            f"   💰 {s['price']:.0f} ₽  |  ⏱ {s['duration']} мин\n"
        )
    await msg.answer("\n".join(lines), parse_mode="HTML")


# ─── Добавление услуги (ДЕМО — данные не пишутся в БД) ───────────────────────

@router.message(F.text == "➕ Добавить услугу")
async def add_service_start(msg: Message, state: FSMContext):
    await state.set_state(AddServiceFSM.waiting_name)
    await msg.answer(
        "Введите <b>название</b> новой услуги:",
        parse_mode="HTML",
    )


@router.message(AddServiceFSM.waiting_name)
async def add_service_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    if not name:
        await msg.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    await state.update_data(name=name)
    await state.set_state(AddServiceFSM.waiting_price)
    await msg.answer(
        f"Услуга: <b>{name}</b>\n\nВведите <b>цену</b> (в рублях, число):",
        parse_mode="HTML",
    )


@router.message(AddServiceFSM.waiting_price)
async def add_service_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.replace(",", ".").strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await msg.answer("Пожалуйста, введите корректную цену (положительное число):")
        return

    await state.update_data(price=price)
    await state.set_state(AddServiceFSM.waiting_duration)
    await msg.answer(
        f"Цена: <b>{price:.0f} ₽</b>\n\n"
        "Введите <b>длительность</b> услуги в минутах (целое число):",
        parse_mode="HTML",
    )


@router.message(AddServiceFSM.waiting_duration)
async def add_service_duration(msg: Message, state: FSMContext):
    try:
        duration = int(msg.text.strip())
        if duration <= 0:
            raise ValueError
    except ValueError:
        await msg.answer("Пожалуйста, введите корректную длительность (целое положительное число):")
        return

    data = await state.get_data()
    await state.clear()

    # ДЕМО: имитируем случайный id, в базу ничего не пишем
    import random
    fake_id = random.randint(10, 99)

    await msg.answer(
        f"✅ Услуга добавлена!\n\n"
        f"#{fake_id} <b>{data['name']}</b>\n"
        f"💰 {data['price']:.0f} ₽  |  ⏱ {duration} мин\n\n"
        f"<i>⚠️ Это демо-режим — услуга не сохранена в базе.</i>",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


# ─── Удаление услуги (ДЕМО — из базы ничего не удаляется) ────────────────────

@router.message(F.text == "🗑 Удалить услугу")
async def delete_service_start(msg: Message):
    services = await db.get_services()
    if not services:
        await msg.answer("Нет услуг для удаления.")
        return
    await msg.answer(
        "Выберите услугу для удаления:",
        reply_markup=services_inline(services, prefix="del"),
    )


@router.callback_query(F.data.startswith("del:"))
async def delete_service_confirm(call: CallbackQuery):
    service_id = int(call.data.split(":")[1])
    service = await db.get_service(service_id)

    if not service:
        await call.answer("Услуга не найдена.", show_alert=True)
        return

    # ДЕМО: показываем успех, но db.delete_service() не вызываем
    await call.message.edit_text(
        f"🗑 Услуга <b>«{service['name']}»</b> удалена.\n\n"
        f"<i>⚠️ Это демо-режим — услуга осталась в базе.</i>",
        parse_mode="HTML",
    )
    await call.answer("Удалено ✅")
