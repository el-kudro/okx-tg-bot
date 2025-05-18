import os
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv
import time
import random

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

last_signal_time = 0

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "✅ Бот активен. Ожидайте сигналы.")

@bot.message_handler(commands=['signal'])
def handle_signal_command(message):
    if message.chat.id != TELEGRAM_USER_ID:
        bot.send_message(message.chat.id, "⛔️ Нет доступа.")
        return
    send_signal()

def send_signal():
    global last_signal_time
    now = time.time()
    coin = random.choice(["BTC", "ETH", "SOL"])
    direction = random.choice(["LONG", "SHORT"])
    price = round(random.uniform(25000, 35000), 2)
    take = round(price * (1.01 if direction == "LONG" else 0.99), 2)
    stop = round(price * (0.99 if direction == "LONG" else 1.01), 2)
    probability = round(random.uniform(70, 99), 2)

    if probability < 90 and now - last_signal_time < 3600:
        print("❌ Вероятность сигнала ниже 90%, не отправляем.")
        return

    if now - last_signal_time < 3600 and probability < 90:
        print("⏳ Сигнал уже был отправлен недавно.")
        return

    text = f"📈 <b>{coin} {direction}</b>\nЦена: {price}\nTP: {take}\nSL: {stop}\n📊 Вероятность: {probability}%"
    bot.send_message(TELEGRAM_USER_ID, text, parse_mode="HTML")
    last_signal_time = now

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        print(">>> [Webhook] Update received")
        if update.message:
            print(f">>> Message received: {update.message.text}")
        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return 'ok', 200

if __name__ == "__main__":
    print(f"[BOOT] BOT_TOKEN: {BOT_TOKEN}")
    print(f"[BOOT] WEBHOOK_URL: {WEBHOOK_URL}")
    print(f"[BOOT] TELEGRAM_USER_ID: {TELEGRAM_USER_ID}")
    app.run(host="0.0.0.0", port=10000)
