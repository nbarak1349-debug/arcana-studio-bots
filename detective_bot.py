#!/usr/bin/env python3
"""
БОТ СЛЕДОВАТЕЛЯ КОЛОБКОВА
Токен берётся из переменной окружения DETECTIVE_BOT_TOKEN
"""

import logging
import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ========== ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ==========
TOKEN = os.environ.get("DETECTIVE_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

if not TOKEN or not ADMIN_ID:
    raise ValueError("Не заданы переменные окружения: DETECTIVE_BOT_TOKEN, ADMIN_ID")

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== СООБЩЕНИЕ СЛЕДОВАТЕЛЯ ==========
DETECTIVE_MESSAGE = """Привет! Извини, что отвлекаю в отпуске, но дело очень важное и странное. Только ты сможешь с ним разобраться, даже дистанционно.

В Доброграде при загадочных обстоятельствах погиб психолог Арсений Новиков. Официальное заключение — самоубийство: выстрел в голову из собственного пистолета, предсмертной записки нет.

Но у меня есть сомнения. Во‑первых, пистолет лежал в правой руке, хотя Новиков был левшой. Во‑вторых, в сейфе явно чего‑то не хватает. И главное — за неделю до смерти он внёс крупную сумму денег, а откуда они взялись — непонятно.

Начальство торопит закрыть дело, но я чувствую: тут что‑то не так.

Все материалы, которые у меня есть, я собрал на сайте: policedobrograd.ru

Изучи всё внимательно. Если найдёшь убийцу — я буду по гроб жизни обязан.

Спасибо, друг!"""

# ========== РАБОТА С ДАННЫМИ ==========
DATA_FILE = "data/players.json"

def load_players():
    """Загружает игроков"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
    return {}

def mark_as_sent(user_id):
    """Отмечает сообщение как отправленное"""
    players = load_players()
    if str(user_id) in players:
        players[str(user_id)]["detective_sent"] = True
        players[str(user_id)]["detective_sent_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(players, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
    return False

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_id = user.id
    
    players = load_players()
    player_data = players.get(str(user_id), {})
    
    if player_data.get("ready"):
        if not player_data.get("detective_sent"):
            await update.message.reply_text(DETECTIVE_MESSAGE)
            mark_as_sent(user_id)
            logger.info(f"✅ Сообщение отправлено игроку {user_id}")
            
            await update.message.reply_text(
                "*Сайт для расследования:* policedobrograd.ru\n\n"
                "Удачи в расследовании! 🕵️",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "Вы уже получили задание. Сайт для расследования: policedobrograd.ru\n\n"
                "Если что-то не работает, напишите @ArcanaStudio_Detective_bot",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            "👮 *Следователь Колобков*\n\n"
            "Я занимаюсь делом Новикова. Кажется, вы еще не зарегистрировались в основном боте.\n\n"
            "*Что делать:*\n"
            "1. Перейдите в бота @ArcanaStudio_Detective_bot\n"
            "2. Нажмите /start\n"
            "3. Пройдите регистрацию\n"
            "4. Вернитесь ко мне\n\n"
            "Я буду ждать!",
            parse_mode="Markdown"
        )

# ========== АДМИН-КОМАНДЫ ==========
async def send_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручная отправка сообщения игроку"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Эта команда только для администратора")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Использование: `/send <ID_игрока>`\n"
            "Пример: `/send 123456789`\n\n"
            "Чтобы отправить всем: `/send_all`",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_id = int(context.args[0])
        await context.bot.send_message(chat_id=target_id, text=DETECTIVE_MESSAGE)
        mark_as_sent(target_id)
        await update.message.reply_text(f"✅ Сообщение отправлено игроку `{target_id}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка всем готовым игрокам"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Эта команда только для администратора")
        return
    
    players = load_players()
    ready_to_send = []
    for user_id_str, data in players.items():
        if data.get("ready") and not data.get("detective_sent"):
            ready_to_send.append((int(user_id_str), data))
    
    if not ready_to_send:
        await update.message.reply_text("✅ Все готовые игроки уже получили сообщение")
        return
    
    await update.message.reply_text(f"⏳ Отправляю {len(ready_to_send)} игрокам...")
    
    success = 0
    failed = 0
    for user_id, _ in ready_to_send:
        try:
            await context.bot.send_message(chat_id=user_id, text=DETECTIVE_MESSAGE)
            mark_as_sent(user_id)
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка отправки {user_id}: {e}")
    
    await update.message.reply_text(f"📊 *ОТЧЕТ ОБ ОТПРАВКЕ:*\n✅ Успешно: {success}\n❌ Ошибок: {failed}", parse_mode="Markdown")

async def detective_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус рассылки"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    players = load_players()
    total = len(players)
    ready = sum(1 for p in players.values() if p.get("ready"))
    sent = sum(1 for p in players.values() if p.get("detective_sent"))
    
    await update.message.reply_text(
        f"📊 *СТАТУС РАССЫЛКИ:*\n"
        f"Всего игроков: {total}\n"
        f"Готовы к игре: {ready}\n"
        f"Получили сообщение: {sent}\n"
        f"Ожидают отправки: {ready - sent}",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка"""
    help_text = """*БОТ-СЛЕДОВАТЕЛЬ КОЛОБКОВ* 👮

*Для игроков:*
/start - получить детективное задание

*Для администратора:*
/send <ID> - отправить сообщение игроку
/send_all - отправить всем готовым
/status - статус рассылки
/help - эта справка"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ========== ЗАПУСК БОТА ==========
def main():
    print("=" * 60)
    print("🚀 ЗАПУСК БОТА-СЛЕДОВАТЕЛЯ КОЛОБКОВА")
    print("=" * 60)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", send_manual))
    app.add_handler(CommandHandler("send_all", send_all))
    app.add_handler(CommandHandler("status", detective_status))
    app.add_handler(CommandHandler("help", help_command))
    
    print("✅ Бот-следователь запущен!")
    print("📱 Ссылка: https://t.me/Kolobkov_police_bot")
    print("\n🛑 Для остановки нажмите Ctrl+C")
    print("=" * 60)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
