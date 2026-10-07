from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select

from config import settings
from database import (
    async_session,
    mark_attendance
)
from models import Booking, DanceGroup, User, Subscription
from keyboards import get_admin_menu_keyboard

admin_router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_id_list

@admin_router.message(F.text == "👑 Панель тренера / студії")
@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Цей розділ лише для керівництва та тренерів студії.")
        return

    await message.answer(
        f"👑 **Панель керування {settings.STUDIO_NAME}**\n\n"
        "Тут ви можете відмітити присутніх на сьогоднішніх тренуваннях (списує заняття автоматично), "
        "переглянути баланси клієнтів або нагадати про оплату.",
        reply_markup=get_admin_menu_keyboard()
    )

@admin_router.callback_query(F.data == "admin_checkin_today")
async def checkin_today(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Немає доступу", show_alert=True)
        return

    today_str = datetime.now().strftime("%Y-%m-%d")

    async with async_session() as session:
        result = await session.execute(
            select(Booking, User, DanceGroup)
            .join(User, Booking.user_id == User.id)
            .join(DanceGroup, Booking.group_id == DanceGroup.id)
            .where(Booking.booking_date == today_str)
        )
        bookings = list(result.all())

    if not bookings:
        await callback.message.answer(
            f"ℹ️ На сьогодні ({today_str}) ще немає записів від клієнтів."
        )
        await callback.answer()
        return

    await callback.message.answer(f"📋 **Записи на сьогодні ({today_str}):**")
    for b, u, g in bookings:
        status_text = "Очікує тренування" if b.status == "booked" else ("Присутній" if b.status == "attended" else "Пропуск")
        ikb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Прийшла (списати)", callback_data=f"att:{b.id}:yes"),
                    InlineKeyboardButton(text="🤒 Хворіла (зберегти)", callback_data=f"att:{b.id}:no")
                ]
            ]
        )
        await callback.message.answer(
            f"👤 **{u.full_name}** ({u.phone or 'без тел.'})\n"
            f"🩰 Напрямок: **{g.name}** о {g.schedule_time}\n"
            f"Статус: {status_text}",
            reply_markup=ikb if b.status == "booked" else None
        )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("att:"))
async def on_attendance_click(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    booking_id = int(parts[1])
    is_yes = parts[2] == "yes"

    success, msg, client_tg_id = await mark_attendance(booking_id, is_yes)
    if success:
        await callback.message.edit_text(
            f"{callback.message.text}\n\n👉 **Результат:** {msg}"
        )
        # Notify client
        if client_tg_id and is_yes:
            try:
                await bot.send_message(
                    chat_id=client_tg_id,
                    text="🩰 **Дякуємо за чудове тренування!**\nТвоє відвідування зараховано. До зустрічі наступного разу! 💕"
                )
            except Exception:
                pass
    else:
        await callback.answer(msg, show_alert=True)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_clients_list")
async def clients_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Немає доступу", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(
            select(User, Subscription)
            .outerjoin(Subscription, (Subscription.user_id == User.id) & (Subscription.is_active == True))
        )
        data = list(result.all())

    lines = [f"👥 **База клієнтів {settings.STUDIO_NAME}:**\n"]
    for u, s in data:
        sub_info = f"{s.title} (залишок: {s.remaining_classes})" if s else "немає активного абонемента"
        lines.append(f"• **{u.full_name}** ({u.phone or '—'}) — {sub_info}")

    msg = "\n".join(lines)
    if len(msg) > 4000:
        msg = msg[:3950] + "\n..."
    await callback.message.answer(msg)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_remind_expiring")
async def remind_expiring(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Немає доступу", show_alert=True)
        return

    async with async_session() as session:
        # Find subscriptions with 1 or 0 remaining classes
        result = await session.execute(
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .where(
                Subscription.is_active == True,
                Subscription.remaining_classes <= 1
            )
        )
        expiring = list(result.all())

    if not expiring:
        await callback.message.answer("Немає клієнтів, у яких закінчується абонемент.")
        await callback.answer()
        return

    sent = 0
    for s, u in expiring:
        try:
            await bot.send_message(
                chat_id=u.telegram_id,
                text=(
                    f"💖 Привіт, {u.full_name}!\n\n"
                    f"Нагадуємо, що в твоєму абонементі залишилось лише **{s.remaining_classes} заняття**.\n"
                    "Щоб не втратити місце в групі, подовж абонемент у розділі «💳 Купити абонемент»!"
                )
            )
            sent += 1
        except Exception:
            pass

    await callback.message.answer(f"📢 Успішно надіслано нагадування {sent} клієнткам!")
    await callback.answer()
