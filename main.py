import os
import time
import threading
import itertools
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from gpt_signal_bot import get_trade_signal
from okx_api import place_order, get_account_balance

# Загрузка переменных
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")

# Инициализация Flask и Telebot
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN)
coin_cycle = itertools.cycle(["BTC", "ETH", "SOL"])
last_signals = {}

# Webhook: обработка входящих обновлений
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return "OK", 200

# Команда /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "✅ Bot is online!\nUse /analyze BTC or /balance.")

# Команда /balance
@bot.message_handler(commands=['balance'])
def handle_balance(message):
    try:
        data = get_account_balance()
        if not data or "data" not in data:
            bot.send_message(message.chat.id, "❌ OKX balance fetch error.")
            return

        balances = data["data"][0].get("details", [])
        msg = "💰 Balance:\n"
        for b in balances:
            if b["ccy"] in ["USDT", "BTC", "ETH", "SOL"] and float(b["availBal"]) > 0:
                msg += f"{b['ccy']}: {b['availBal']}\n"

        if msg.strip() == "💰 Balance:":
            msg += "Empty wallet."
        bot.send_message(message.chat.id, msg)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Balance error: {e}")

# Команда /analyze <coin>
@bot.message_handler(func=lambda m: m.text.lower().startswith("/analyze"))
def handle_analyze(message):
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "Use: /analyze BTC | ETH | SOL")
            return
        coin = parts[1].upper()
        signal = get_trade_signal(coin)
        send_signal_to_user(message.chat.id, coin, signal)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Analyze error: {e}")

# Отправка сигнала
def send_signal_to_user(user_id, coin, signal):
    if not signal:
        bot.send_message(user_id, f"❌ No signal for {coin}")
        return

    price = next((s for s in signal.split() if s.replace('.', '', 1).isdigit()), None)
    inst_id = f"{coin}-USDT"
    last_signals[user_id] = {"inst_id": inst_id, "price": price}

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"✅ Enter trade {coin}", callback_data=f"enter_trade_{coin.lower()}"))
    bot.send_message(user_id, signal, reply_markup=markup)

# Обработка кнопки входа в сделку
@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_trade_"))
def handle_trade(call):
    data = last_signals.get(call.message.chat.id)
    if not data:
        bot.send_message(call.message.chat.id, "⚠️ Signal not found.")
        return

    response = place_order(
        inst_id=data["inst_id"],
        side="buy",
        px=data["price"] or "market",
        ord_type="market",
        sz=TRADE_AMOUNT
    )
    bot.send_message(call.message.chat.id, f"✅ Order sent: {response}")

# Фоновый автосканнер
def auto_market_scan():
    while True:
        coin = next(coin_cycle)
        now = datetime.now().time()
        signal = get_trade_signal(coin)

        probability = 0
        for line in signal.split("\n"):
            if "%" in line:
                try:
                    probability = int(''.join(filter(str.isdigit, line)))
                except:
                    probability = 0
                break

        if not (10 <= now.hour <= 23) or probability >= 90:
            send_signal_to_user(TELEGRAM_USER_ID, coin, signal)

        time.sleep(3600)

# Запуск Webhook и Flask-сервера
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL.rstrip('/')}/{BOT_TOKEN}")
    threading.Thread(target=auto_market_scan).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
