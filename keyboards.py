from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from typing import List
from models import DanceGroup

def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="🩰 Записатися на тренування")],
        [KeyboardButton(text="🎟 Мій абонемент"), KeyboardButton(text="📅 Розклад студії")],
        [KeyboardButton(text="📍 Локація та Контакти"), KeyboardButton(text="💳 Купити абонемент")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="👑 Панель тренера / студії")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        is_persistent=True
    )

def get_contact_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поділитися номером телефону", request_contact=True)],
            [KeyboardButton(text="Пропустити")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_groups_keyboard(groups: List[DanceGroup]) -> InlineKeyboardMarkup:
    inline_keyboard = []
    for g in groups:
        btn_text = f"{g.name} ({g.schedule_days} о {g.schedule_time})"
        inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"book_group:{g.id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

def get_subscription_plans_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✨ Пробне тренування — 150 грн", callback_data="buy_plan:trial:1:150")
            ],
            [
                InlineKeyboardButton(text="🔥 Абонемент 8 занять — 1200 грн", callback_data="buy_plan:8:8:1200")
            ],
            [
                InlineKeyboardButton(text="👑 Абонемент 12 занять — 1600 грн", callback_data="buy_plan:12:12:1600")
            ],
            [
                InlineKeyboardButton(text="👠 High Heels (Разове) — 200 грн", callback_data="buy_plan:single:1:200")
            ],
            [
                InlineKeyboardButton(text="💬 Написати адміністратору в Direct", url="https://instagram.com/leo_danceee_studio")
            ]
        ]
    )

from aiogram.types import WebAppInfo

def get_admin_menu_keyboard(webapp_url: str = "https://leodanceapp.loca.lt/app") -> InlineKeyboardMarkup:
    buttons = []
    if webapp_url and webapp_url.startswith("https://"):
        buttons.append([
            InlineKeyboardButton(text="📱 Відкрити додаток тренера (Mini App)", web_app=WebAppInfo(url=webapp_url))
        ])
    
    buttons.extend([
        [
            InlineKeyboardButton(text="📋 Відмітити присутність на сьогодні", callback_data="admin_checkin_today")
        ],
        [
            InlineKeyboardButton(text="👥 Список клієнтів та баланс занять", callback_data="admin_clients_list")
        ],
        [
            InlineKeyboardButton(text="📢 Розіслати нагадування про абонементи", callback_data="admin_remind_expiring")
        ]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
