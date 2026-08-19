import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    ChatPermissions,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ТВОЙ TELEGRAM ID
ADMIN_ID = 8798104630

CONFIG_FILE = Path("config.json")


# ============================================================
# ЦЕНЫ ПО УМОЛЧАНИЮ
# ============================================================

DEFAULT_CONFIG = {
    "ban_3h": 50,
    "ban_6h": 80,
    "ban_12h": 120,
    "ban_24h": 160,
    "ban_permanent": 500,

    "mute_3h": 30,
    "mute_6h": 40,
    "mute_9h": 45,
    "mute_12h": 60,

    "unban": 200,
    "unmute": 50,
}


# ============================================================
# ЛОГИ
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG.JSON
# ============================================================

def load_config():
    try:
        if not CONFIG_FILE.exists():
            save_config(DEFAULT_CONFIG.copy())
            return DEFAULT_CONFIG.copy()

        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        changed = False

        for key, value in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = value
                changed = True

        if changed:
            save_config(data)

        return data

    except Exception as e:
        logger.error("Ошибка загрузки config.json: %s", e)
        return DEFAULT_CONFIG.copy()


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )


config = load_config()


# ============================================================
# ТОВАРЫ
# ============================================================

PRODUCTS = {
    "ban_3h": {
        "name": "🔨 Бан на 3 часа",
        "type": "ban",
        "hours": 3,
    },

    "ban_6h": {
        "name": "🔨 Бан на 6 часов",
        "type": "ban",
        "hours": 6,
    },

    "ban_12h": {
        "name": "🔨 Бан на 12 часов",
        "type": "ban",
        "hours": 12,
    },

    "ban_24h": {
        "name": "🔨 Бан на 24 часа",
        "type": "ban",
        "hours": 24,
    },

    "ban_permanent": {
        "name": "🔨 Вечный бан",
        "type": "ban_permanent",
        "hours": None,
    },

    "mute_3h": {
        "name": "🔇 Мут на 3 часа",
        "type": "mute",
        "hours": 3,
    },

    "mute_6h": {
        "name": "🔇 Мут на 6 часов",
        "type": "mute",
        "hours": 6,
    },

    "mute_9h": {
        "name": "🔇 Мут на 9 часов",
        "type": "mute",
        "hours": 9,
    },

    "mute_12h": {
        "name": "🔇 Мут на 12 часов",
        "type": "mute",
        "hours": 12,
    },

    "unban": {
        "name": "🔓 Разбан",
        "type": "unban",
        "hours": None,
    },

    "unmute": {
        "name": "🔊 Снять мут",
        "type": "unmute",
        "hours": None,
    },
}


# ============================================================
# ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛒 Магазин",
                callback_data="shop"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ Помощь",
                callback_data="help"
            )
        ]
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛒 Магазин",
                callback_data="shop"
            )
        ],
        [
            InlineKeyboardButton(
                "⚙️ Управление ценами",
                callback_data="prices"
            )
        ],
        [
            InlineKeyboardButton(
                "💰 Баланс Stars",
                callback_data="balance"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 Все цены",
                callback_data="show_prices"
            )
        ]
    ])


def shop_menu():
    buttons = []

    # БАНЫ
    buttons.append([
        InlineKeyboardButton(
            "🔨 БАНЫ",
            callback_data="nothing"
        )
    ])

    for key in [
        "ban_3h",
        "ban_6h",
        "ban_12h",
        "ban_24h",
        "ban_permanent",
    ]:
        product = PRODUCTS[key]
        price = config[key]

        buttons.append([
            InlineKeyboardButton(
                f"{product['name']} — {price} ⭐",
                callback_data=f"buy:{key}"
            )
        ])

    # МУТЫ
    buttons.append([
        InlineKeyboardButton(
            "🔇 МУТЫ",
            callback_data="nothing"
        )
    ])

    for key in [
        "mute_3h",
        "mute_6h",
        "mute_9h",
        "mute_12h",
    ]:
        product = PRODUCTS[key]
        price = config[key]

        buttons.append([
            InlineKeyboardButton(
                f"{product['name']} — {price} ⭐",
                callback_data=f"buy:{key}"
            )
        ])

    # СНЯТИЕ
    buttons.append([
        InlineKeyboardButton(
            "🔓 СНЯТИЕ НАКАЗАНИЯ",
            callback_data="nothing"
        )
    ])

    for key in [
        "unban",
        "unmute",
    ]:
        product = PRODUCTS[key]
        price = config[key]

        buttons.append([
            InlineKeyboardButton(
                f"{product['name']} — {price} ⭐",
                callback_data=f"buy:{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="main"
        )
    ])

    return InlineKeyboardMarkup(buttons)


def prices_menu():
    buttons = []

    for key, product in PRODUCTS.items():

        buttons.append([
            InlineKeyboardButton(
                f"{product['name']} — {config[key]} ⭐",
                callback_data=f"price:{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="admin"
        )
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "🤖 <b>Action Shop</b>\n\n"
        "Добро пожаловать!\n\n"
        "Здесь можно приобрести действия "
        "для Telegram-чата за ⭐ Stars.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# ============================================================
# ADMIN
# ============================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ У вас нет доступа к админ-панели."
        )
        return

    await update.message.reply_text(
        "👑 <b>Админ-панель</b>\n\n"
        "Добро пожаловать, владелец!",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # --------------------------------------------------------
    # ПУСТАЯ КНОПКА
    # --------------------------------------------------------

    if data == "nothing":
        return

    # --------------------------------------------------------
    # ГЛАВНОЕ МЕНЮ
    # --------------------------------------------------------

    if data == "main":

        context.user_data.clear()

        await query.edit_message_text(
            "🤖 <b>Action Shop</b>\n\n"
            "Выберите нужный раздел:",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )

        return

    # --------------------------------------------------------
    # АДМИНКА
    # --------------------------------------------------------

    if data == "admin":

        if not is_admin(user_id):
            await query.edit_message_text(
                "❌ Доступ запрещён."
            )
            return

        await query.edit_message_text(
            "👑 <b>Админ-панель</b>",
            parse_mode="HTML",
            reply_markup=admin_menu(),
        )

        return

    # --------------------------------------------------------
    # МАГАЗИН
    # --------------------------------------------------------

    if data == "shop":

        context.user_data.clear()

        await query.edit_message_text(
            "🛒 <b>Магазин действий</b>\n\n"
            "Выберите необходимое действие:",
            parse_mode="HTML",
            reply_markup=shop
