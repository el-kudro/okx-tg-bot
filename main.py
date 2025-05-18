import os
import telebot
from flask import Flask, request
from dotenv import load_dotenv
import time
import random

# Загрузка переменных среды
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", "0.01"))

# Инициализация бота и Flask
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Отметка времени последнего сигнала
last_signal_time = 0

# === Хендлеры ===

@bot.message_handler(commands=['start'])
def handle_start(message):
    print(f">>> /start от {message.chat.id}")
    bot.send_message(message.chat.id, "✅ Бот работает. Готов к сигналам.")

@bot.message_handler(commands=['signal'])
def handle_signal(message):
    print(f">>> /signal от {message.chat.id}")
    if message.chat.id != TELEGRAM_USER_ID:
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к сигналам.")
        return
    send_trade_signal()

def send_trade_signal():
    global last_signal_time
    now = time.time()

    # Если прошло менее 3600 секунд (1 час) и вероятность < 90%, не отправляем сигнал
    probability = round(random.uniform(80, 99), 2)
    if probability < 90 and now - last_signal_time < 3600:
        print("⏳ Сигнал пропущен: вероятность < 90% и лимит 1 в час")
        return

    last_signal_time = now
    symbol = random.choice(['BTC', 'ETH', 'SOL'])
    direction = random.choice(['LONG', 'SHORT'])
    entry_price = round(random.uniform(25000, 35000), 2)
    tp = round(entry_price * (1.01 if direction == 'LONG' else 0.99), 2)
    sl = round(entry_price * (0.99 if direction == 'LONG' else 1.01), 2)

    msg = f"""📢 <b>{symbol} {direction}</b>
💰 Цена входа: {entry_price}
🎯 TP: {tp}
🛑 SL: {sl}
📊 Уверенность: {probability}%
"""
    bot.send_message(TELEGRAM_USER_ID, msg, parse_mode='HTML')
    print("✅ Сигнал отправлен")

# === Обработка Webhook ===

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        print(">>> [Webhook] Update received!")
        if update.message:
            print(f">>> Message received: {update.message.text}")
        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Ошибка обработки Webhook: {e}")
    return "ok", 200

# === Точка входа ===

if __name__ == "__main__":
    print(f"[BOOT] BOT_TOKEN: {BOT_TOKEN}")
    print(f"[BOOT] WEBHOOK_URL: {WEBHOOK_URL}")
    print(f"[BOOT] TELEGRAM_USER_ID: {TELEGRAM_USER_ID}")
    print(f"[BOOT] TRADE_AMOUNT: {TRADE_AMOUNT}")
    app.run(host='0.0.0.0', port=10000)
