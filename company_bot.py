#!/usr/bin/env python3
"""
БОТ КОМПАНИИ ARCANA STUDIO (с аналитикой)
Токены берутся из переменных окружения
"""

import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("COMPANY_BOT_TOKEN")
DETECTIVE_TOKEN = os.environ.get("DETECTIVE_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

if not TOKEN or not DETECTIVE_TOKEN or not ADMIN_ID:
    raise ValueError("Не заданы переменные окружения: COMPANY_BOT_TOKEN, DETECTIVE_BOT_TOKEN, ADMIN_ID")

# ========== СОСТОЯНИЯ ДИАЛОГА ==========
START, FREE_ACCESS, GET_NAME, GET_PHONE, CONFIRM, READY = range(6)

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== РАБОТА С ДАННЫМИ ==========
DATA_FILE = "data/players.json"

def init_data():
    """Создаёт файл данных и папку data, если их нет"""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def load_players():
    """Загружает всех игроков из JSON"""
    init_data()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_player(user_id, data):
    """Сохраняет или обновляет данные игрока"""
    players = load_players()
    user_id_str = str(user_id)
    if user_id_str in players:
        players[user_id_str].update(data)
    else:
        players[user_id_str] = data
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

def update_player_step(user_id, step_name, additional_data=None):
    """Универсальная функция для логирования шага и сохранения данных"""
    user_id_str = str(user_id)
    players = load_players()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if user_id_str not in players:
        players[user_id_str] = {}
    
    # Сохраняем шаг с меткой времени
    players[user_id_str][f"step_{step_name}"] = now
    if additional_data:
        players[user_id_str].update(additional_data)
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

def mark_ready(user_id):
    """Отмечает игрока готовым"""
    update_player_step(user_id, "ready", {"ready": True, "ready_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

def mark_detective_sent(user_id):
    """Отмечает, что детектив отправлен"""
    players = load_players()
    user_id_str = str(user_id)
    if user_id_str in players:
        players[user_id_str]["detective_sent"] = True
        players[user_id_str]["detective_sent_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(players, f, ensure_ascii=False, indent=2)

# ========== ОСНОВНОЙ ДИАЛОГ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Команда /start - тизер игры"""
    user = update.effective_user
    user_id = user.id
    
    # Логируем начало
    update_player_step(user_id, "start", {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    })
    
    teaser = """🔍 *ДЕТЕКТИВНЫЙ ARG-КВЕСТ «ЭФФЕКТ ЯНУСА»*

Доброград, тихий город на берегу моря. Здесь все знают друг друга.

Вчера в собственном кабинете найден мёртвым известный психолог Арсений Новиков. Официальная версия — самоубийство. Но старый следователь Колобков уверен: это убийство.

Проблема в том, что все улики указывают на разных людей. Жена, любовница, партнёр по бизнесу, криминальный кредитор, муж погибшей пациентки… У каждого был мотив.

*Только вы сможете разобраться в этом клубке лжи.*

👇 *Готовы начать расследование?*"""
    
    keyboard = [[InlineKeyboardButton("🚀 НАЧАТЬ РАССЛЕДОВАНИЕ", callback_data="begin")]]
    
    await update.message.reply_text(
        teaser,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    context.user_data["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context.user_data["user_id"] = user_id
    
    return START

async def begin_investigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало расследования (нажатие кнопки)"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Логируем шаг
    update_player_step(user_id, "begin")
    
    message = """🎫 *ДОСТУП К МАТЕРИАЛАМ ДЕЛА*

Для получения полного доступа к материалам дела требуется оформить пропуск.

*Внимание: Сейчас идет бета-тестирование — доступ БЕСПЛАТНЫЙ!*

Вы получите:
• Полный доступ к почте Новикова
• Базы данных полиции Доброграда
• Расшифровки аудиозаписей
• Файлы проекта «Янус»

Нажмите кнопку ниже для получения доступа."""
    
    keyboard = [[InlineKeyboardButton("🎫 ПОЛУЧИТЬ БЕСПЛАТНЫЙ ДОСТУП", callback_data="free_access")]]
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return FREE_ACCESS

async def free_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Клик по кнопке бесплатного доступа"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Логируем шаг
    update_player_step(user_id, "free_access")
    
    message = """📋 *РЕГИСТРАЦИЯ ДЛЯ ДОСТУПА*

Почти готово! Для связи по делу и отправки улик нам нужны ваши контакты.

*Пожалуйста, введите ваше имя (или имя капитана команды):*"""
    
    await query.edit_message_text(message, parse_mode="Markdown")
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем имя"""
    name = update.message.text.strip()
    user_id = update.effective_user.id
    
    if len(name) < 2:
        await update.message.reply_text("Пожалуйста, введите настоящее имя (минимум 2 символа):")
        return GET_NAME
    
    # Логируем шаг с именем
    update_player_step(user_id, "name_input", {"name": name})
    context.user_data["name"] = name
    
    message = f"""📞 *НОМЕР ТЕЛЕФОНА*

Отлично, *{name}*!

Теперь введите ваш *номер телефона* (в любом формате):

*Пример:* +7 999 123-45-67 или 89991234567

*Важно:* Этот номер будет использоваться только для связи по делу."""
    
    await update.message.reply_text(message, parse_mode="Markdown")
    return GET_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получаем телефон"""
    phone = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Простая валидация
    if len(phone) < 5:
        await update.message.reply_text("Пожалуйста, введите корректный номер телефона:")
        return GET_PHONE
    
    # Логируем шаг с телефоном
    update_player_step(user_id, "phone_input", {"phone": phone})
    context.user_data["phone"] = phone
    
    message = f"""✅ *ДАННЫЕ ПРИНЯТЫ*

Проверьте ваши данные:
┌──────────────────────
│ *Имя:* {context.user_data['name']}
│ *Телефон:* {phone}
│ *Дата регистрации:* {datetime.now().strftime('%d.%m.%Y %H:%M')}
└──────────────────────

*ВАЖНО!*
1. Убедитесь, что в настройках Telegram у вас разрешены «Входящие сообщения»
   (Настройки → Конфиденциальность → Сообщения → «Все»)
2. После подтверждения вы получите сообщение от следователя

*Все верно?*"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ ВСЁ ВЕРНО", callback_data="confirm"),
            InlineKeyboardButton("✏️ ИСПРАВИТЬ", callback_data="restart")
        ]
    ]
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM

async def confirm_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение данных"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    # Логируем подтверждение
    update_player_step(user_id, "confirm")
    
    message = """🎉 *РЕГИСТРАЦИЯ ЗАВЕРШЕНА!*

Доступ к материалам дела открыт!

*Вы готовы приступить к расследованию прямо сейчас?*

⚠️ *После подтверждения:* 
1. Вам придет сообщение от следователя Колобкова
2. Вы получите доступ к сайту с материалами дела"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ ДА, ГОТОВ!", callback_data="ready"),
            InlineKeyboardButton("⏳ ПОЗЖЕ", callback_data="later")
        ]
    ]
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return READY

async def restart_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Перезапуск регистрации (исправить данные)"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Введите ваше имя заново:",
        parse_mode="Markdown"
    )
    return GET_NAME

async def player_ready(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Игрок готов - отправляем детектива"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_id = user.id
    name = context.user_data.get("name", "")
    
    # Логируем готовность
    mark_ready(user_id)
    
    # Отправляем сообщение от детектива
    detective_sent = await send_detective_message(user_id, name)
    
    if detective_sent:
        mark_detective_sent(user_id)
        
        final_message = f"""🔍 *ИГРА НАЧАЛАСЬ!*

Вам отправлено сообщение от следователя Колобкова (@Kolobkov_police_bot)

*Сайт для начала расследования:*
policedobrograd.ru

*Что делать дальше:*
1. Проверьте сообщение от @Kolobkov_police_bot
2. Перейдите на сайт policedobrograd.ru
3. Начните изучать материалы дела

Удачи в расследовании! Помните — каждая деталь имеет значение.

🕵️ *Погружайтесь в дело...*"""
        
        await query.edit_message_text(
            final_message,
            parse_mode="Markdown"
        )
    else:
        # Если автоматически не отправилось
        keyboard = [[InlineKeyboardButton("📨 ПЕРЕЙТИ К СЛЕДОВАТЕЛЮ", url="https://t.me/Kolobkov_police_bot")]]
        await query.edit_message_text(
            f"""✅ Вы готовы к игре!

*Чтобы получить задание:*
1. Перейдите к боту следователя: @Kolobkov_police_bot
2. Нажмите /start

*Сайт для расследования:* policedobrograd.ru""",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Уведомление админу
    await notify_admin_new_player(user_id, name, context.user_data.get('phone', 'не указан'), user.username)
    
    return ConversationHandler.END

async def player_later(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Игрок выбрал 'Позже'"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Хорошо! Когда будете готовы, напишите /start в этом чате.\n\n"
        "Доступ к делу уже открыт для вас.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена регистрации"""
    await update.message.reply_text(
        "Регистрация отменена. Если передумаете — напишите /start",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ========== ОТПРАВКА ДЕТЕКТИВА ==========
async def send_detective_message(user_id, name):
    """Отправляет сообщение от второго бота"""
    try:
        detective_bot = Bot(token=DETECTIVE_TOKEN)
        message = """Привет! Извини, что отвлекаю в отпуске, но дело очень важное и странное. Только ты сможешь с ним разобраться, даже дистанционно.

В Доброграде при загадочных обстоятельствах погиб психолог Арсений Новиков. Официальное заключение — самоубийство: выстрел в голову из собственного пистолета, предсмертной записки нет.

Но у меня есть сомнения. Во‑первых, пистолет лежал в правой руке, хотя Новиков был левшой. Во‑вторых, в сейфе явно чего‑то не хватает. И главное — за неделю до смерти он внёс крупную сумму денег, а откуда они взялись — непонятно.

Начальство торопит закрыть дело, но я чувствую: тут что‑то не так.

Все материалы, которые у меня есть, я собрал на сайте: policedobrograd.ru

Изучи всё внимательно. Если найдёшь убийцу — я буду по гроб жизни обязан.

Спасибо, друг!"""
        await detective_bot.send_message(chat_id=user_id, text=message)
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки от детектива: {e}")
        return False

async def notify_admin_new_player(user_id, name, phone, username):
    """Уведомление админу о новом готовом игроке"""
    try:
        admin_bot = Bot(token=TOKEN)
        admin_message = (
            f"🎯 *НОВЫЙ ИГРОК ГОТОВ К ИГРЕ!*\n"
            f"ID: `{user_id}`\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Username: @{username or 'нет'}\n"
            f"Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
        )
        await admin_bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления админу: {e}")

# ========== АДМИН-КОМАНДЫ ==========
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Расширенная статистика для админа"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Эта команда только для администратора")
        return
    
    players = load_players()
    
    # Подсчёт по шагам
    total_start = len(players)
    
    step_counts = {
        "begin": 0,
        "free_access": 0,
        "name_input": 0,
        "phone_input": 0,
        "confirm": 0,
        "ready": 0,
        "detective_sent": 0,
    }
    
    for uid, data in players.items():
        if "step_begin" in data:
            step_counts["begin"] += 1
        if "step_free_access" in data:
            step_counts["free_access"] += 1
        if "step_name_input" in data:
            step_counts["name_input"] += 1
        if "step_phone_input" in data:
            step_counts["phone_input"] += 1
        if "step_confirm" in data:
            step_counts["confirm"] += 1
        if data.get("ready"):
            step_counts["ready"] += 1
        if data.get("detective_sent"):
            step_counts["detective_sent"] += 1
    
    # Конверсия
    def conv(from_count, to_count):
        if from_count == 0:
            return "0%"
        return f"{to_count / from_count * 100:.1f}%"
    
    # Статистика по времени (сегодня, вчера, неделя)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    def count_since(date):
        cnt = 0
        for data in players.values():
            reg = data.get("registered")
            if reg and datetime.strptime(reg, "%Y-%m-%d %H:%M:%S").date() >= date:
                cnt += 1
        return cnt
    
    today_new = count_since(today)
    yesterday_new = count_since(yesterday) - today_new
    week_new = count_since(week_ago)
    
    message = (
        f"📊 *СТАТИСТИКА БОТА*\n"
        f"Всего уникальных пользователей (кто нажал /start): {total_start}\n\n"
        f"*Воронка шагов:*\n"
        f"▶️ Начали расследование (begin): {step_counts['begin']} ({conv(total_start, step_counts['begin'])} от старта)\n"
        f"🎫 Нажали «получить доступ»: {step_counts['free_access']} ({conv(step_counts['begin'], step_counts['free_access'])} от begin)\n"
        f"👤 Ввели имя: {step_counts['name_input']} ({conv(step_counts['free_access'], step_counts['name_input'])})\n"
        f"📞 Ввели телефон: {step_counts['phone_input']} ({conv(step_counts['name_input'], step_counts['phone_input'])})\n"
        f"✅ Подтвердили данные: {step_counts['confirm']} ({conv(step_counts['phone_input'], step_counts['confirm'])})\n"
        f"🕵️ Готовы играть (ready): {step_counts['ready']} ({conv(step_counts['confirm'], step_counts['ready'])})\n"
        f"📨 Получили детектива: {step_counts['detective_sent']} ({conv(step_counts['ready'], step_counts['detective_sent'])})\n\n"
        f"*Новые регистрации:*\n"
        f"Сегодня: {today_new}\n"
        f"Вчера: {yesterday_new}\n"
        f"За 7 дней: {week_new}\n"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")

# ========== ЗАПУСК БОТА ==========
def main():
    print("=" * 60)
    print("🚀 ЗАПУСК БОТА КОМПАНИИ ARCANA STUDIO (с аналитикой)")
    print("=" * 60)
    
    init_data()
    
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            START: [CallbackQueryHandler(begin_investigation, pattern="^begin$")],
            FREE_ACCESS: [CallbackQueryHandler(free_access, pattern="^free_access$")],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CONFIRM: [
                CallbackQueryHandler(confirm_data, pattern="^confirm$"),
                CallbackQueryHandler(restart_registration, pattern="^restart$")
            ],
            READY: [
                CallbackQueryHandler(player_ready, pattern="^ready$"),
                CallbackQueryHandler(player_later, pattern="^later$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stats", admin_stats))
    
    print("✅ Бот компании запущен!")
    print("📱 Ссылка: https://t.me/ArcanaStudio_Detective_bot")
    print("\n💡 Команды для админа:")
    print("  /stats - расширенная статистика")
    print("\n🛑 Для остановки нажмите Ctrl+C")
    print("=" * 60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
