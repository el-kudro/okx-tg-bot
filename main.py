import os
import time
import random
import threading
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

# Инициализация Flask и Telebot
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Последняя отправка сигнала
last_signal_time = 0

# Команды
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "✅ Бот запущен. Доступные команды: /balance, /signal")

@bot.message_handler(commands=['balance'])
def handle_balance(message):
    if message.chat.id != TELEGRAM_USER_ID:
        return
    data = get_account_balance()
    if not data or "data" not in data:
        bot.send_message(message.chat.id, f"❌ Ошибка OKX: {data.get('msg', 'Нет ответа')}")
        return
    balances = data["data"][0].get("details", [])
    filtered = [b for b in balances if b["ccy"] in ["USDT", "BTC", "ETH", "SOL"] and float(b["availBal"]) > 0]
    if not filtered:
        bot.send_message(message.chat.id, "Кошелёк пуст или нет активов.")
        return
    msg = "💰 Баланс:\n" + "\n".join(f"{b['ccy']}: {b['availBal']}" for b in filtered)
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['signal'])
def handle_signal(message):
    if message.chat.id != TELEGRAM_USER_ID:
        return
    send_trade_signal()

# Автоотправка сигнала в фоне
def auto_signal_loop():
    global last_signal_time
    while True:
        try:
            now = time.time()
            if now - last_signal_time >= 3600:
                print("[AUTO] ⏰ Проверка на сигнал по таймеру")
                send_trade_signal()
            time.sleep(60)
        except Exception as e:
            print(f"[AUTO] ❌ Ошибка автоанализа: {e}")
            time.sleep(60)

# Функция отправки сигнала
def send_trade_signal():
    global last_signal_time

    symbol = random.choice(["BTC", "ETH", "SOL"])
    response = get_trade_signal(symbol)

    if "❌" in response:
        bot.send_message(TELEGRAM_USER_ID, response)
        return

    prob = extract_probability(response)
    print(f"[SIGNAL] {symbol} | Вероятность: {prob}%")

    if prob < 90 and time.time() - last_signal_time < 3600:
        print(f"⏳ Пропущено: {symbol}, вероятность {prob}% < 90 и уже был сигнал < 1ч")
        return

    last_signal_time = time.time()
    bot.send_message(TELEGRAM_USER_ID, f"📡 GPT сигнал по {symbol}:\n\n{response}")

def extract_probability(text):
    try:
        for line in text.splitlines():
            if "%" in line:
                numbers = [float(s.replace('%', '')) for s in line.split() if "%" in s]
                if numbers:
                    return numbers[0]
    except:
        pass
    return 0

# Webhook
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Ошибка Webhook: {e}")
    return "ok", 200

# Запуск
if __name__ == "__main__":
    print(f"[BOOT] ✅ Запуск с Webhook на {WEBHOOK_URL}/{BOT_TOKEN}")
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    threading.Thread(target=auto_signal_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
