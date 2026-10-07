from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart

from config import settings
from database import (
    get_or_create_user,
    get_user_by_telegram_id,
    get_active_subscription,
    get_all_groups,
    get_group_by_id,
    create_booking,
    get_user_bookings,
    add_subscription
)
from keyboards import (
    get_main_menu_keyboard,
    get_contact_request_keyboard,
    get_groups_keyboard,
    get_subscription_plans_keyboard
)

client_router = Router()

@client_router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.full_name or "Красуне"
    
    # Parse deeplink argument (e.g. /start trial_heels or /start trial_kids)
    args = message.text.split(maxsplit=1)
    payload = args[1].strip() if len(args) > 1 else "organic"

    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=user_name,
        source=payload
    )

    is_admin = message.from_user.id in settings.admin_id_list

    # Targeted Welcome Messages based on campaign funnel
    if payload == "trial_heels":
        welcome_text = (
            f"👠 **Привіт, {user_name}! Спеціальна пропозиція на High Heels від Leo Dance!**\n\n"
            "Ти перейшла за посиланням з Instagram на **пробне заняття High Heels** у Дрогобичі.\n\n"
            "📍 **Локація:** вул. Грушевського 148 Б\n"
            "🕒 **Групи:** Вівторок та Четвер (19:00 або 20:00 для початківців)\n"
            "🔥 **Вартість першого пробного:** лише 150 грн (замість 200 грн)!\n\n"
            "Натисни **«🩰 Записатися на тренування»** нижче, щоб забронювати місце в залі на цей тиждень 👇"
        )
    elif payload == "trial_kids":
        welcome_text = (
            f"🌟 **Вітаємо в Leo Dance Studio, {user_name}!**\n\n"
            "Ви перейшли для запису дитини на танці / гімнастику в Дрогобичі.\n\n"
            "• Набір діток від 3-х років (групи 3-4, 4-5, 6-8, 9-11, 12-15 років)\n"
            "• Безпечний, просторий зал на Грушевського 148 Б\n\n"
            "🎁 **Перше пробне заняття для вашої дитини безкоштовне або зі знижкою!**\n"
            "Оберіть вікову групу в меню нижче для бронювання 👇"
        )
    else:
        welcome_text = (
            f"✨ **Ласкаво просимо до {settings.STUDIO_NAME}!** ✨\n\n"
            f"Привіт, **{user_name}**! Ми раді бачити тебе в просторі танцю, естетики та грації.\n\n"
            f"📍 Локація: **м. {settings.STUDIO_CITY}, {settings.STUDIO_ADDRESS}**\n\n"
            "🎁 **Тобі нараховано 1 пробне тренування!**\n"
            "Обирай напрямок у меню нижче та записуйся на своє перше заняття 👇"
        )

    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(is_admin))

@client_router.message(F.text == "🎟 Мій абонемент")
async def my_subscription(message: Message):
    user = await get_user_by_telegram_id(message.from_user.id)
    if not user:
        user = await get_or_create_user(message.from_user.id, message.from_user.full_name)

    sub = await get_active_subscription(user.id)
    bookings = await get_user_bookings(user.id)

    if not sub:
        sub_info = "❌ **У вас зараз немає активного абонемента.**\nОберіть зручний тариф через кнопку «💳 Купити абонемент»."
    else:
        exp_date = sub.expires_at.strftime("%d.%m.%Y") if sub.expires_at else "безстроковий"
        sub_info = (
            f"🎟 **Твій активний абонемент:**\n"
            f"• Тариф: **{sub.title}**\n"
            f"• Залишок занять: **{sub.remaining_classes} з {sub.total_classes}**\n"
            f"• Дійсний до: **{exp_date}**"
        )

    bookings_text = ""
    if bookings:
        bookings_text = "\n\n📌 **Твої найближчі записи:**\n"
        for b, g in bookings:
            status_emoji = "✅" if b.status == "booked" else ("🩰" if b.status == "attended" else "⚠️")
            bookings_text += f"{status_emoji} **{g.name}** ({b.booking_date} о {g.schedule_time})\n"

    await message.answer(f"{sub_info}{bookings_text}")

@client_router.message(F.text == "📅 Розклад студії")
async def show_schedule(message: Message):
    schedule_text = (
        f"📅 **РОЗКЛАД ЗАНЯТЬ — {settings.STUDIO_NAME}**\n"
        f"📍 {settings.STUDIO_ADDRESS}\n\n"
        "🖤 **ПОНЕДІЛОК / СЕРЕДА:**\n"
        "• 16:00 — Діти (6-8 років)\n"
        "• 17:20 — Діти (9-11 років)\n"
        "• 18:30 — Малюки (4-5 років) — 1 група\n"
        "• 19:20 — Малюки (4-5 років) — 2 група\n\n"
        "🖤 **ВІВТОРОК / ЧЕТВЕР:**\n"
        "• 16:00 — Діти (8-10 років)\n"
        "• 17:00 — Підлітки (12-15 років)\n"
        "• 18:15 — Малюки (3-4 рочки)\n"
        "• 19:00 — **High Heels (Основна група)** 🔥\n"
        "• 20:00 — **High Heels (Початківці)** 👠\n\n"
        "🖤 **П'ЯТНИЦЯ:**\n"
        "• 18:00 — **CHOREO** ✨\n\n"
        "Натисни **«🩰 Записатися на тренування»**, щоб забронювати місце в залі!"
    )
    await message.answer(schedule_text)

@client_router.message(F.text == "📍 Локація та Контакти")
async def show_contacts(message: Message):
    contacts_text = (
        f"🏢 **{settings.STUDIO_NAME}**\n\n"
        f"📍 **Адреса:** м. {settings.STUDIO_CITY}, {settings.STUDIO_ADDRESS}\n"
        f"📞 **Телефон:** +380983223561\n"
        f"👑 **Керівник:** [@_ireeendtk](https://instagram.com/_ireeendtk)\n"
        f"📸 **Instagram:** [@{settings.STUDIO_INSTAGRAM}](https://instagram.com/{settings.STUDIO_INSTAGRAM})\n"
        f"🥊 **Боксерський клуб-партнер:** [@{settings.STUDIO_BOXING_CLUB}](https://instagram.com/{settings.STUDIO_BOXING_CLUB})\n\n"
        "Чекаємо тебе на тренуваннях! 💕"
    )
    await message.answer(contacts_text)

@client_router.message(F.text == "💳 Купити абонемент")
async def buy_sub(message: Message):
    await message.answer(
        "💳 **Оберіть абонемент у студії Leo Dance:**\n\n"
        "Кожен абонемент діє 30 днів з моменту активації. "
        "У разі хвороби чи поважної причини заняття зберігаються за умови попередження адміністратора.",
        reply_markup=get_subscription_plans_keyboard()
    )

@client_router.callback_query(F.data.startswith("buy_plan:"))
async def on_plan_select(callback: CallbackQuery):
    parts = callback.data.split(":")
    plan_type = parts[1]
    classes = int(parts[2])
    price = float(parts[3])

    user = await get_or_create_user(callback.from_user.id, callback.from_user.full_name)
    titles = {
        "trial": "Пробне заняття",
        "8": "Абонемент на 8 занять",
        "12": "Абонемент на 12 занять",
        "single": "Разове заняття High Heels"
    }
    title = titles.get(plan_type, "Абонемент")

    # For demo pilot: activate subscription immediately
    sub = await add_subscription(user.id, title, classes, price)

    await callback.message.edit_text(
        f"🎉 **Вітаємо! Абонемент активовано!**\n\n"
        f"• Назва: **{title}**\n"
        f"• Кількість занять: **{classes}**\n"
        f"• Вартість: **{int(price)} грн**\n\n"
        "Тепер ти можеш записатися на найближче тренування через кнопку **«🩰 Записатися на тренування»**!"
    )
    await callback.answer()

@client_router.message(F.text == "🩰 Записатися на тренування")
async def start_booking(message: Message):
    groups = await get_all_groups()
    await message.answer(
        "💃 **Оберіть групу або напрямок для запису:**\n\n"
        "*(Кількість місць у залі обмежена для вашого комфорту)*",
        reply_markup=get_groups_keyboard(groups)
    )

@client_router.callback_query(F.data.startswith("book_group:"))
async def on_group_booked(callback: CallbackQuery):
    group_id = int(callback.data.split("book_group:")[1])
    group = await get_group_by_id(group_id)
    if not group:
        await callback.answer("Групу не знайдено", show_alert=True)
        return

    user = await get_or_create_user(callback.from_user.id, callback.from_user.full_name)
    sub = await get_active_subscription(user.id)
    if not sub:
        await callback.message.answer(
            "⚠️ **У вас немає активного абонемента або закінчилися заняття!**\n\n"
            "Придбайте абонемент у розділі «💳 Купити абонемент» перед записом.",
            reply_markup=get_subscription_plans_keyboard()
        )
        await callback.answer()
        return

    # book for the next session date
    today = datetime.now()
    target_date = today.strftime("%Y-%m-%d")

    success, msg = await create_booking(user.id, group.id, target_date)
    if success:
        await callback.message.edit_text(
            f"✅ **Чудово! Ти записана!** 💕\n\n"
            f"🩰 Напрямок: **{group.name}**\n"
            f"🕒 Час: **{group.schedule_days} о {group.schedule_time}**\n"
            f"📍 Локація: **{settings.STUDIO_ADDRESS}**\n"
            f"Тренер: **{group.trainer_name}**\n\n"
            f"Ми надішлемо тобі нагадування перед початком заняття. До зустрічі в залі!"
        )
    else:
        await callback.message.edit_text(f"⚠️ {msg}")
    await callback.answer()
