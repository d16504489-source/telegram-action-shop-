import os
import json
import logging
from pathlib import Path
from datetime import timedelta

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
# ОСНОВНЫЕ НАСТРОЙКИ
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ТВОЙ TELEGRAM ID
ADMIN_ID = 8798104630

CONFIG_FILE = Path("config.json")


# ============================================================
# ЦЕНЫ ПО УМОЛЧАНИЮ
# ============================================================

DEFAULT_CONFIG = {
    "ban": 500,
    "ban_7d": 250,
    "mute_24h": 100,
    "mute_7d": 300,
    "unban": 700,
    "unmute": 150
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
# РАБОТА С CONFIG.JSON
# ============================================================

def load_config():
    try:
        if not CONFIG_FILE.exists():
            CONFIG_FILE.write_text(
                json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
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
        json.dump(data, file, indent=4, ensure_ascii=False)


config = load_config()


# ============================================================
# НАЗВАНИЯ ТОВАРОВ
# ============================================================

PRODUCTS = {
    "ban": {
        "name": "🔨 Вечный бан",
        "description": "Перманентно заблокировать пользователя в выбранном чате.",
    },
    "ban_7d": {
        "name": "⏳ Бан на 7 дней",
        "description": "Заблокировать пользователя на 7 дней.",
    },
    "mute_24h": {
        "name": "🔇 Мут на 24 часа",
        "description": "Запретить пользователю отправлять сообщения на 24 часа.",
    },
    "mute_7d": {
        "name": "👻 Мут на 7 дней",
        "description": "Запретить пользователю отправлять сообщения на 7 дней.",
    },
    "unban": {
        "name": "🔓 Разбан",
        "description": "Снять бан с пользователя.",
    },
    "unmute": {
        "name": "🔊 Снять мут",
        "description": "Снять ограничение на отправку сообщений.",
    },
}


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        ],
        [
            InlineKeyboardButton("💰 Баланс Stars", callback_data="balance"),
        ],
        [
            InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
        ],
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
        ],
        [
            InlineKeyboardButton("⚙️ Изменить цены", callback_data="prices"),
        ],
        [
            InlineKeyboardButton("💰 Баланс Stars", callback_data="balance"),
        ],
        [
            InlineKeyboardButton("📋 Все цены", callback_data="show_prices"),
        ],
    ])


def shop_menu():
    buttons = []

    for key, product in PRODUCTS.items():
        price = config.get(key, DEFAULT_CONFIG[key])

        buttons.append([
            InlineKeyboardButton(
                f"{product['name']} — {price} ⭐",
                callback_data=f"buy:{key}",
            )
        ])

    buttons.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="main")
    ])

    return InlineKeyboardMarkup(buttons)


def prices_menu():
    buttons = []

    for key, product in PRODUCTS.items():
        price = config.get(key, DEFAULT_CONFIG[key])

        buttons.append([
            InlineKeyboardButton(
                f"{product['name']} — {price} ⭐",
                callback_data=f"price:{key}",
            )
        ])

    buttons.append([
        InlineKeyboardButton("⬅️ Назад", callback_data="admin")
    ])

    return InlineKeyboardMarkup(buttons)


# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        "🤖 <b>Action Shop</b>\n\n"
        "Добро пожаловать!\n\n"
        "Здесь можно приобрести действия для Telegram-чата "
        "за ⭐ Telegram Stars.\n\n"
        "Выберите нужный раздел:"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# ============================================================
# /ADMIN
# ============================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ У вас нет доступа к этой панели."
        )
        return

    await update.message.reply_text(
        "👑 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


# ============================================================
# CALLBACK КНОПКИ
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
    # ГЛАВНОЕ МЕНЮ
    # --------------------------------------------------------

    if data == "main":
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
            "👑 <b>Панель администратора</b>",
            parse_mode="HTML",
            reply_markup=admin_menu(),
        )
        return

    # --------------------------------------------------------
    # МАГАЗИН
    # --------------------------------------------------------

    if data == "shop":
        await query.edit_message_text(
            "🛒 <b>Магазин действий</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=shop_menu(),
        )
        return

    # --------------------------------------------------------
    # БАЛАНС STARS
    # --------------------------------------------------------

    if data == "balance":
        try:
            balance = await context.bot.get_my_star_balance()

            await query.edit_message_text(
                f"💰 <b>Баланс бота</b>\n\n"
                f"⭐ {balance.amount} Stars",
                parse_mode="HTML",
                reply_markup=main_menu(),
            )

        except TelegramError as e:
            logger.error("Ошибка получения баланса: %s", e)

            await query.edit_message_text(
                "❌ Не удалось получить баланс Stars.",
                reply_markup=main_menu(),
            )

        return

    # --------------------------------------------------------
    # ПОМОЩЬ
    # --------------------------------------------------------

    if data == "help":
        await query.edit_message_text(
            "ℹ️ <b>Как это работает?</b>\n\n"
            "1️⃣ Выберите действие.\n"
            "2️⃣ Укажите ID чата.\n"
            "3️⃣ Укажите ID пользователя.\n"
            "4️⃣ Проверьте заказ.\n"
            "5️⃣ Оплатите его Stars.\n"
            "6️⃣ После успешной оплаты бот выполнит действие.\n\n"
            "⚠️ Бот должен быть администратором чата "
            "с необходимыми правами.",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        return

    # --------------------------------------------------------
    # ВЫБОР ТОВАРА
    # --------------------------------------------------------

    if data.startswith("buy:"):
        product_key = data.split(":", 1)[1]

        if product_key not in PRODUCTS:
            await query.edit_message_text(
                "❌ Товар не найден.",
                reply_markup=shop_menu(),
            )
            return

        context.user_data["product"] = product_key
        context.user_data["step"] = "chat_id"

        product = PRODUCTS[product_key]
        price = config[product_key]

        await query.edit_message_text(
            f"{product['name']}\n\n"
            f"💰 Цена: <b>{price} ⭐</b>\n\n"
            f"💬 Введите <b>ID чата</b>, в котором нужно выполнить действие.\n\n"
            f"Пример:\n"
            f"<code>-1001234567890</code>",
            parse_mode="HTML",
        )
        return

    # --------------------------------------------------------
    # ИЗМЕНЕНИЕ ЦЕН
    # --------------------------------------------------------

    if data == "prices":
        if not is_admin(user_id):
            await query.edit_message_text(
                "❌ Доступ запрещён."
            )
            return

        await query.edit_message_text(
            "⚙️ <b>Управление ценами</b>\n\n"
            "Выберите товар:",
            parse_mode="HTML",
            reply_markup=prices_menu(),
        )
        return

    # --------------------------------------------------------
    # ВЫБОР ЦЕНЫ
    # --------------------------------------------------------

    if data.startswith("price:"):
        if not is_admin(user_id):
            await query.edit_message_text(
                "❌ Доступ запрещён."
            )
            return

        product_key = data.split(":", 1)[1]

        if product_key not in PRODUCTS:
            return

        context.user_data["editing_price"] = product_key
        context.user_data["step"] = "new_price"

        product = PRODUCTS[product_key]
        current_price = config[product_key]

        await query.edit_message_text(
            f"⚙️ <b>Изменение цены</b>\n\n"
            f"{product['name']}\n"
            f"Текущая цена: <b>{current_price} ⭐</b>\n\n"
            f"Введите новую цену в Stars:",
            parse_mode="HTML",
        )
        return

    # --------------------------------------------------------
    # ПОКАЗ ЦЕН
    # --------------------------------------------------------

    if data == "show_prices":
        if not is_admin(user_id):
            await query.edit_message_text(
                "❌ Доступ запрещён."
            )
            return

        text = "📋 <b>Текущие цены</b>\n\n"

        for key, product in PRODUCTS.items():
            text += (
                f"{product['name']} — "
                f"<b>{config[key]} ⭐</b>\n"
            )

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=admin_menu(),
        )

        return


# ============================================================
# ОБРАБОТКА ТЕКСТА
# ============================================================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    text = update.message.text.strip()

    step = context.user_data.get("step")

    # --------------------------------------------------------
    # ИЗМЕНЕНИЕ ЦЕНЫ
    # --------------------------------------------------------

    if step == "new_price":

        if not is_admin(user.id):
            return

        try:
            new_price = int(text)

            if new_price < 1:
                raise ValueError

            if new_price > 25000:
                await update.message.reply_text(
                    "❌ Максимальная цена — 25 000 ⭐."
                )
                return

        except ValueError:
            await update.message.reply_text(
                "❌ Введите целое число.\n\n"
                "Например: <code>750</code>",
                parse_mode="HTML",
            )
            return

        product_key = context.user_data.get("editing_price")

        if product_key not in PRODUCTS:
            context.user_data.clear()
            await update.message.reply_text(
                "❌ Ошибка. Попробуйте снова через /admin."
            )
            return

        config[product_key] = new_price
        save_config(config)

        product = PRODUCTS[product_key]

        context.user_data.clear()

        await update.message.reply_text(
            f"✅ <b>Цена изменена</b>\n\n"
            f"{product['name']}\n"
            f"Новая цена: <b>{new_price} ⭐</b>",
            parse_mode="HTML",
            reply_markup=admin_menu(),
        )

        return

    # --------------------------------------------------------
    # ВВОД ID ЧАТА
    # --------------------------------------------------------

    if step == "chat_id":

        try:
            chat_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ ID чата должен быть числом.\n\n"
                "Пример:\n"
                "<code>-1001234567890</code>",
                parse_mode="HTML",
            )
            return

        product_key = context.user_data.get("product")

        if product_key not in PRODUCTS:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Заказ устарел. Откройте магазин заново.",
                reply_markup=main_menu(),
            )
            return

        # Проверяем существование чата
        try:
            chat = await context.bot.get_chat(chat_id)
        except TelegramError:
            await update.message.reply_text(
                "❌ Не удалось найти этот чат.\n\n"
                "Убедитесь, что бот добавлен в него."
            )
            return

        # Проверяем права самого бота
        try:
            bot_member = await context.bot.get_chat_member(
                chat_id,
                context.bot.id,
            )

            if bot_member.status != "administrator":
                await update.message.reply_text(
                    "❌ Бот не является администратором этого чата."
                )
                return

            if not getattr(
                bot_member,
                "can_restrict_members",
                False
            ):
                await update.message.reply_text(
                    "❌ У бота нет права "
                    "«Блокировать пользователей»."
                )
                return

        except TelegramError:
            await update.message.reply_text(
                "❌ Не удалось проверить права бота."
            )
            return

        context.user_data["chat_id"] = chat_id
        context.user_data["step"] = "target_id"

        await update.message.reply_text(
            f"💬 Чат найден:\n"
            f"<b>{chat.title}</b>\n\n"
            f"👤 Теперь введите <b>Telegram ID пользователя</b>, "
            f"к которому нужно применить действие.\n\n"
            f"Пример:\n"
            f"<code>123456789</code>",
            parse_mode="HTML",
        )

        return

    # --------------------------------------------------------
    # ВВОД ID ПОЛЬЗОВАТЕЛЯ
    # --------------------------------------------------------

    if step == "target_id":

        try:
            target_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ ID пользователя должен быть числом.\n\n"
                "Пример:\n"
                "<code>123456789</code>",
                parse_mode="HTML",
            )
            return

        chat_id = context.user_data.get("chat_id")
        product_key = context.user_data.get("product")

        if not chat_id or product_key not in PRODUCTS:
            context.user_data.clear()

            await update.message.reply_text(
                "❌ Заказ устарел. Начните заново.",
                reply_markup=main_menu(),
            )
            return

        # Проверяем пользователя в чате
        try:
            member = await context.bot.get_chat_member(
                chat_id,
                target_id,
            )
        except TelegramError:
            await update.message.reply_text(
                "❌ Пользователь не найден в этом чате.\n\n"
                "Проверьте Telegram ID."
            )
            return

        # Нельзя покупать действие против владельца чата
        if member.status == "creator":
            await update.message.reply_text(
                "❌ Нельзя применить это действие "
                "к владельцу чата."
            )
            return

        # Нельзя покупать действие против администратора
        if member.status == "administrator":
            await update.message.reply_text(
                "❌ Нельзя применить это действие "
                "к администратору."
            )
            return

        product = PRODUCTS[product_key]
        price = config[product_key]

        context.user_data["target_id"] = target_id
        context.user_data["step"] = "confirm"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"💳 Оплатить {price} ⭐",
                    callback_data="confirm_payment",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data="cancel_order",
                )
            ]
        ])

        await update.message.reply_text(
            f"🧾 <b>Проверка заказа</b>\n\n"
            f"🎯 Действие: {product['name']}\n"
            f"💬 Чат ID: <code>{chat_id}</code>\n"
            f"👤 Пользователь ID: <code>{target_id}</code>\n"
            f"💰 Стоимость: <b>{price} ⭐</b>\n\n"
            f"После успешной оплаты действие будет выполнено автоматически.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )

        return


# ============================================================
# ПОДТВЕРЖДЕНИЕ ОПЛАТЫ
# ============================================================

async def confirm_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    product_key = context.user_data.get("product")
    chat_id = context.user_data.get("chat_id")
    target_id = context.user_data.get("target_id")

    if not product_key or not chat_id or not target_id:
        await query.edit_message_text(
            "❌ Заказ устарел. Начните покупку заново."
        )
        return

    price = config.get(product_key)

    if not price:
        await query.edit_message_text(
            "❌ Цена товара не найдена."
        )
        return

    # --------------------------------------------------------
    # ФИНАЛЬНАЯ ПРОВЕРКА ПЕРЕД ОПЛАТОЙ
    # --------------------------------------------------------

    try:
        bot_member = await context.bot.get_chat_member(
            chat_id,
            context.bot.id,
        )

        if bot_member.status != "administrator":
            await query.edit_message_text(
                "❌ Бот больше не является администратором чата."
            )
            return

        if not getattr(
            bot_member,
            "can_restrict_members",
            False
        ):
            await query.edit_message_text(
                "❌ У бота нет права блокировать/ограничивать участников."
            )
            return

        target_member = await context.bot.get_chat_member(
            chat_id,
            target_id,
        )

        if target_member.status in ("creator", "administrator"):
            await query.edit_message_text(
                "❌ Нельзя применить действие к администратору."
            )
            return

    except TelegramError:
        await query.edit_message_text(
            "❌ Не удалось проверить чат или пользователя."
        )
        return

    # --------------------------------------------------------
    # PAYLOAD
    # --------------------------------------------------------

    payload = (
        f"{product_key}|"
        f"{chat_id}|"
        f"{target_id}|"
        f"{user_id}|"
        f"{price}"
    )

    # Payload должен быть коротким
    if len(payload.encode("utf-8")) > 128:
        await query.edit_message_text(
            "❌ Ошибка заказа: слишком длинные данные."
        )
        return

    product = PRODUCTS[product_key]

    try:
        await context.bot.send_invoice(
            chat_id=user_id,
            title=product["name"],
            description=(
                f"{product['description']} "
                f"Стоимость: {price} Telegram Stars."
            ),
            payload=payload,
            currency="XTR",
            prices=[
                LabeledPrice(
                    product["name"],
                    price,
                )
            ],
            provider_token="",
        )

        await query.edit_message_text(
            "💳 <b>Счёт отправлен!</b>\n\n"
            f"Товар: {product['name']}\n"
            f"Стоимость: <b>{price} ⭐</b>\n\n"
            "Оплатите счёт выше.",
            parse_mode="HTML",
        )

    except TelegramError as e:
        logger.error("Ошибка отправки invoice: %s", e)

        await query.edit_message_text(
            "❌ Не удалось создать счёт на оплату."
        )


# ============================================================
# ОТМЕНА ЗАКАЗА
# ============================================================

async def cancel_order(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    await query.edit_message_text(
        "❌ Заказ отменён.",
        reply_markup=main_menu(),
    )


# ============================================================
# PRE-CHECKOUT
# ============================================================

async def precheckout_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.pre_checkout_query

    try:
        payload = query.invoice_payload

        parts = payload.split("|")

        if len(parts) != 5:
            await query.answer(
                ok=False,
                error_message="Некорректный заказ.",
            )
            return

        product_key, chat_id, target_id, buyer_id, price = parts

        price = int(price)
        buyer_id = int(buyer_id)

        current_price = config.get(product_key)

        if current_price != price:
            await query.answer(
                ok=False,
                error_message=(
                    "Цена товара изменилась. "
                    "Создайте новый заказ."
                ),
            )
            return

        if query.from_user.id != buyer_id:
            await query.answer(
                ok=False,
                error_message="Этот счёт предназначен другому пользователю.",
            )
            return

        if query.currency != "XTR":
            await query.answer(
                ok=False,
                error_message="Неверная валюта.",
            )
            return

        if query.total_amount != price:
            await query.answer(
                ok=False,
                error_message="Неверная сумма оплаты.",
            )
            return

        await query.answer(ok=True)

    except Exception as e:
        logger.error("Ошибка pre-checkout: %s", e)

        await query.answer(
            ok=False,
            error_message="Ошибка проверки заказа.",
        )


# ============================================================
# УСПЕШНАЯ ОПЛАТА
# ============================================================

async def successful_payment_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message
    payment = message.successful_payment

    try:
        payload = payment.invoice_payload

        parts = payload.split("|")

        if len(parts) != 5:
            await message.reply_text(
                "❌ Некорректный платёж."
            )
            return

        product_key, chat_id, target_id, buyer_id, price = parts

        chat_id = int(chat_id)
        target_id = int(target_id)
        buyer_id = int(buyer_id)
        price = int(price)

        # ----------------------------------------------------
        # ПРОВЕРКА ПЛАТЕЖА
        # ----------------------------------------------------

        if payment.currency != "XTR":
            await message.reply_text(
                "❌ Неверная валюта платежа."
            )
            return

        if payment.total_amount != price:
            await message.reply_text(
                "❌ Неверная сумма платежа."
            )
            return

        if message.from_user.id != buyer_id:
            await message.reply_text(
                "❌ Платёж не соответствует заказу."
            )
            return

        # ----------------------------------------------------
        # ВЫПОЛНЕНИЕ ДЕЙСТВИЯ
        # ----------------------------------------------------

        success = await execute_action(
            context,
            product_key,
            chat_id,
            target_id,
        )

        if success:
            product_name = PRODUCTS[product_key]["name"]

            await message.reply_text(
                "✅ <b>Заказ выполнен!</b>\n\n"
                f"🎯 {product_name}\n"
                f"👤 ID: <code>{target_id}</code>\n"
                f"💬 Чат: <code>{chat_id}</code>\n"
                f"💰 Оплачено: <b>{price} ⭐</b>",
                parse_mode="HTML",
            )

        else:
            # ------------------------------------------------
            # ЕСЛИ ДЕЙСТВИЕ НЕ УДАЛОСЬ —
            # ПЫТАЕМСЯ ВЕРНУТЬ STARS
            # ------------------------------------------------

            try:
                await context.bot.refund_star_payment(
                    user_id=buyer_id,
                    telegram_payment_charge_id=(
                        payment.telegram_payment_charge_id
                    ),
                )

                await message.reply_text(
                    "❌ Не удалось выполнить действие.\n\n"
                    f"💰 <b>{price} ⭐</b> возвращены.",
                    parse_mode="HTML",
                )

            except TelegramError as refund_error:

                logger.error(
                    "Ошибка возврата Stars: %s",
                    refund_error,
                )

                await message.reply_text(
                    "❌ Не удалось выполнить действие.\n\n"
                    "⚠️ Автоматический возврат Stars "
                    "не удалось выполнить. Обратитесь к администратору."
                )

    except Exception as e:
        logger.exception(
            "Ошибка обработки успешного платежа: %s",
            e,
        )

        await message.reply_text(
            "❌ Произошла ошибка при выполнении заказа."
        )


# ============================================================
# ВЫПОЛНЕНИЕ ДЕЙСТВИЯ
# ============================================================

async def execute_action(
    context: ContextTypes.DEFAULT_TYPE,
    product_key: str,
    chat_id: int,
    target_id: int,
) -> bool:

    try:

        # ----------------------------------------------------
        # ВЕЧНЫЙ БАН
        # ----------------------------------------------------

        if product_key == "ban":

            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=target_id,
            )

            return True

        # ----------------------------------------------------
        # БАН 7 ДНЕЙ
        # ----------------------------------------------------

        if product_key == "ban_7d":

            until_date = (
                __import__("datetime")
                .datetime.now(
                    __import__("datetime").timezone.utc
                )
                + timedelta(days=7)
            )

            await context.bot.ban_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                until_date=until_date,
            )

            return True

        # ----------------------------------------------------
        # МУТ 24 ЧАСА
        # ----------------------------------------------------

        if product_key == "mute_24h":

            until_date = (
                __import__("datetime")
                .datetime.now(
                    __import__("datetime").timezone.utc
                )
                + timedelta(hours=24)
            )

            permissions = ChatPermissions(
                can_send_messages=False
            )

            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                permissions=permissions,
                until_date=until_date,
            )

            return True

        # ----------------------------------------------------
        # МУТ 7 ДНЕЙ
        # ----------------------------------------------------

        if product_key == "mute_7d":

            until_date = (
                __import__("datetime")
                .datetime.now(
                    __import__("datetime").timezone.utc
                )
                + timedelta(days=7)
            )

            permissions = ChatPermissions(
                can_send_messages=False
            )

            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                permissions=permissions,
                until_date=until_date,
            )

            return True

        # ----------------------------------------------------
        # РАЗБАН
        # ----------------------------------------------------

        if product_key == "unban":

            await context.bot.unban_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                only_if_banned=True,
            )

            return True

        # ----------------------------------------------------
        # СНЯТЬ МУТ
        # ----------------------------------------------------

        if product_key == "unmute":

            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
                can_manage_topics=False,
            )

            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=target_id,
                permissions=permissions,
            )

            return True

        return False

    except TelegramError as e:
        logger.error(
            "Ошибка выполнения действия %s: %s",
            product_key,
            e,
        )

        return False


# ============================================================
# ОШИБКИ
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.exception(
        "Произошла ошибка:",
        exc_info=context.error,
    )


# ============================================================
# ЗАПУСК
# ============================================================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN. "
            "Добавьте переменную BOT_TOKEN в Render."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Команды
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("admin", admin_command)
    )

    # Кнопки
    application.add_handler(
        CallbackQueryHandler(
            confirm_payment,
            pattern=r"^confirm_payment$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            cancel_order,
            pattern=r"^cancel_order$",
        )
    )

    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    # Текстовые сообщения
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    # Pre-checkout
    application.add_handler(
        PreCheckoutQueryHandler(
            precheckout_callback
        )
    )

    # Успешная оплата
    application.add_handler(
        MessageHandler(
            filters.SUCCESSFUL_PAYMENT,
            successful_payment_callback,
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info("Бот запущен.")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
