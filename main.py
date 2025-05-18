import os
import time
import threading
import random
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from gpt_signal_bot import get_trade_signal
from okx_api import get_account_balance

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", "0.01"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
last_signal_time = 0
AUTO_SIGNAL_INTERVAL = 3600  # 1 час

# Команды
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "✅ Бот запущен. Используй /signal или /balance")

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    data = get_account_balance()
    try:
        if not data or "data" not in data:
            bot.send_message(message.chat.id, f"⚠️ Ошибка OKX: {data.get('msg', 'Unknown error')}")
            return
        balances = data["data"][0]["details"]
        filtered = [b for b in balances if b["ccy"] in ["USDT", "BTC", "ETH", "SOL"] and float(b["availBal"]) > 0]
        if not filtered:
            bot.send_message(message.chat.id, "Кошелёк пуст или нет активов.")
            return
        msg = "💰 Баланс:\n" + "\n".join([f"{b['ccy']}: {b['availBal']}" for b in filtered])
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка парсинга: {e}")

@bot.message_handler(commands=['signal'])
def handle_signal(message):
    if message.chat.id != TELEGRAM_USER_ID:
        bot.send_message(message.chat.id, "⛔️ Нет доступа")
        return
    send_trade_signal()

def send_trade_signal():
    global last_signal_time
    now = time.time()
    symbol = random.choice(["BTC", "ETH", "SOL"])
    response = get_trade_signal(symbol)
    
    if "❌" in response:
        bot.send_message(TELEGRAM_USER_ID, response)
        return

    probability = extract_probability(response)
    if probability < 90 and now - last_signal_time < AUTO_SIGNAL_INTERVAL:
        print("⏳ Пропущено: вероятность < 90% и не прошло 1 час")
        return

    last_signal_time = now
    msg = f"📢 <b>{symbol} сигнал</b>\n\n{response}"
    bot.send_message(TELEGRAM_USER_ID, msg, parse_mode='HTML')
    print("✅ Сигнал отправлен")

def extract_probability(text):
    for line in text.split("\n"):
        if "%" in line:
            try:
                return float(line.strip().replace("%", "").replace("Probability", "").strip())
            except:
                pass
    return 0.0

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
        print(">>> [Webhook] Update received")
        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Ошибка Webhook: {e}")
    return "ok", 200

def auto_loop():
    while True:
        try:
            send_trade_signal()
        except Exception as e:
            print(f"❌ Ошибка в авто-цикле: {e}")
        time.sleep(60)

# Запуск
if __name__ == "__main__":
    print("[BOOT] Бот стартует...")
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    threading.Thread(target=auto_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
