import os
import telebot
from flask import Flask, request
from dotenv import load_dotenv
import time
import random

# === Load env ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", "0.01"))

# === Init bot and app ===
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

last_signal_time = 0

# === Handlers ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    print(f">>> [handle_start] Отправляю приветствие в чат {message.chat.id}")
    bot.send_message(message.chat.id, "✅ Бот запущен и ждет сигналов!")

@bot.message_handler(commands=['signal'])
def handle_signal(message):
    if message.chat.id != TELEGRAM_USER_ID:
        bot.send_message(message.chat.id, "⛔️ Доступ запрещён.")
        return
    send_signal()

def send_signal():
    global last_signal_time
    now = time.time()

    coin = random.choice(["BTC", "ETH", "SOL"])
    direction = random.choice(["LONG", "SHORT"])
    price = round(random.uniform(25000, 35000), 2)
    tp = round(price * (1.01 if direction == "LONG" else 0.99), 2)
    sl = round(price * (0.99 if direction == "LONG" else 1.01), 2)
    prob = round(random.uniform(80, 99), 2)

    if prob < 90 and now - last_signal_time < 3600:
        print("⏳ Пропущено: Низкая вероятность и таймер")
        return

    last_signal_time = now

    msg = f"""📢 <b>{coin} {direction}</b>
💵 Цена: {price}
🎯 TP: {tp}
🛑 SL: {sl}
📊 Уверенность: {prob}%
"""
    bot.send_message(TELEGRAM_USER_ID, msg, parse_mode="HTML")

# === Webhook endpoint ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def receive_update():
    try:
        data = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(data)
        print(">>> [Webhook] Update received!")
        if update.message:
            print(f">>> Message received: {update.message.text}")
        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Ошибка Webhook: {e}")
    return "ok", 200

# === Entry point ===
if __name__ == "__main__":
    print(f"[BOOT] BOT_TOKEN: {BOT_TOKEN}")
    print(f"[BOOT] WEBHOOK_URL: {WEBHOOK_URL}")
    print(f"[BOOT] TELEGRAM_USER_ID: {TELEGRAM_USER_ID}")
    print(f"[BOOT] TRADE_AMOUNT: {TRADE_AMOUNT}")
    app.run(host="0.0.0.0", port=10000)
