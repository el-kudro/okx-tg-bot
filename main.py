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

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

print(f"[BOOT] BOT_TOKEN: {BOT_TOKEN}")
print(f"[BOOT] WEBHOOK_URL: {WEBHOOK_URL}")
print(f"[BOOT] TELEGRAM_USER_ID: {TELEGRAM_USER_ID}")
print(f"[BOOT] TRADE_AMOUNT: {TRADE_AMOUNT}")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
coin_cycle = itertools.cycle(["BTC", "ETH", "SOL"])
last_signals = {}

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    print(">>> /start received")
    bot.send_message(message.chat.id, "🤖 Bot is active. Waiting for signals...")

# Команда /balance
@bot.message_handler(commands=['balance'])
def show_balance(message):
    data = get_account_balance()
    try:
        if not data or "data" not in data:
            bot.send_message(message.chat.id, f"⚠️ OKX error: {data.get('msg', 'Unknown error')}")
            return

        balances = data["data"][0]["details"]
        filtered = [b for b in balances if b["ccy"] in ["USDT", "BTC", "ETH", "SOL"] and float(b["availBal"]) > 0]
        if not filtered:
            bot.send_message(message.chat.id, "Wallet is empty or has no supported assets.")
            return

        msg = "💰 Current balance:\n"
        for b in filtered:
            msg += f"{b['ccy']}: {b['availBal']}\n"
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error parsing balance: {e}")

# Фоновый анализ рынка (раз в час)
def auto_market_scan():
    while True:
        print(">>> Running hourly market scan...")
        best_signal = None
        best_coin = None
        best_prob = 0

        for _ in range(3):
            coin = next(coin_cycle)
            signal = get_trade_signal(coin)
            probability = extract_probability(signal)
            print(f">>> {coin} signal prob: {probability}%")

            if probability > best_prob:
                best_signal = signal
                best_coin = coin
                best_prob = probability

        now = datetime.now().time()
        restricted_start = datetime.strptime("10:00", "%H:%M").time()
        restricted_end = datetime.strptime("23:00", "%H:%M").time()

        if restricted_start <= now <= restricted_end and best_prob < 90:
            print(">>> Signal skipped (low confidence during restricted hours)")
        else:
            send_signal_to_user(TELEGRAM_USER_ID, best_coin, best_signal)

        time.sleep(3600)  # ждать 1 час

def extract_probability(signal):
    probability = 0
    for line in signal.split("\n"):
        if "%" in line:
            digits = ''.join([c for c in line if c.isdigit()])
            try:
                probability = int(digits)
            except:
                probability = 0
            break
    return probability

# Отправка сигнала пользователю
def send_signal_to_user(user_id, coin, signal):
    price = None
    probability_line = "?"
    probability_value = 0

    try:
        for line in signal.split("\n"):
            if "entry" in line.lower() or "вход" in line.lower():
                numbers = [s for s in line.split() if s.replace('.', '', 1).isdigit()]
                if numbers:
                    price = numbers[0]
            if "%" in line or "probab" in line.lower():
                probability_line = line.strip()
                digits = ''.join([c for c in line if c.isdigit()])
                probability_value = int(digits)
    except:
        price = None

    if signal and price:
        inst_id = f"{coin}-USDT"
        last_signals[user_id] = {"inst_id": inst_id, "price": price}

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✅ Enter trade {coin}", callback_data=f"enter_trade_{coin.lower()}"))

        full_signal = f"{signal}\n\n📊 {probability_line if '%' in probability_line else 'Success probability: ~70%'}"
        bot.send_message(user_id, full_signal, reply_markup=markup)

# Обработка нажатия кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_trade_"))
def execute_trade(call):
    user_id = call.message.chat.id
    data = last_signals.get(user_id)

    if not data:
        bot.send_message(user_id, "⚠️ Signal not found.")
        return

    inst_id = data["inst_id"]
    price = data["price"] or "market"

    response = place_order(
        inst_id=inst_id,
        side="buy",
        px=price,
        ord_type="market",
        sz=TRADE_AMOUNT
    )

    bot.send_message(user_id, f"✅ Order sent to {inst_id}: {response}")

# Webhook маршрут
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def receive_update():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)

        print(">>> [Webhook] Update received!")
        if update.message:
            print(f">>> Message received: {update.message.text}")
        elif update.callback_query:
            print(f">>> Callback received: {update.callback_query.data}")

        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return "OK", 200

# Запуск
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    # Фоновый сканер
    threading.Thread(target=auto_market_scan, daemon=True).start()

    # Flask запуск
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
