import os
import time
import threading
from datetime import datetime
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from gpt_signal_bot import get_trade_signal
from okx_api import place_order

# Загрузка переменных окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Хранение последнего сигнала
last_signal = {}

# Обработка нажатия кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_trade_"))
def execute_trade(call):
    user_id = call.message.chat.id
    data = last_signal.get(user_id)

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

# Получение и отправка лучшего сигнала
def scan_best_trade():
    while True:
        best_coin = None
        best_signal = None
        best_prob = 0
        coins = ["BTC", "ETH", "SOL"]

        for coin in coins:
            signal = get_trade_signal(coin)
            for line in signal.split("\n"):
                if "%" in line:
                    digits = ''.join([c for c in line if c.isdigit()])
                    try:
                        prob = int(digits)
                        if prob > best_prob:
                            best_prob = prob
                            best_coin = coin
                            best_signal = signal
                    except:
                        continue
                    break

        if best_coin and best_signal:
            now = datetime.now().time()
            restricted_start = datetime.strptime("10:00", "%H:%M").time()
            restricted_end = datetime.strptime("23:00", "%H:%M").time()

            if best_prob >= 90 or not (restricted_start <= now <= restricted_end):
                send_signal(best_coin, best_signal)

        time.sleep(3600)  # раз в час

def send_signal(coin, signal):
    user_id = TELEGRAM_USER_ID
    price = None
    for line in signal.split("\n"):
        if "entry" in line.lower():
            price = next((s for s in line.split() if s.replace('.', '', 1).isdigit()), None)
            break

    inst_id = f"{coin}-USDT"
    last_signal[user_id] = {"inst_id": inst_id, "price": price}

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"✅ Enter trade {coin}", callback_data=f"enter_trade_{coin.lower()}"))

    bot.send_message(user_id, f"{signal}", reply_markup=markup)

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def receive_update():
    update = telebot.types.Update.de_json(request.data.decode("utf-8"))
    print(">>> [Webhook] Обновление получено")
    bot.process_new_updates([update])
    return "ok", 200

if __name__ == "__main__":
    print(f"[BOOT] BOT_TOKEN: {BOT_TOKEN}")
    print(f"[BOOT] WEBHOOK_URL: {WEBHOOK_URL}")
    print(f"[BOOT] TELEGRAM_USER_ID: {TELEGRAM_USER_ID}")
    print(f"[BOOT] TRADE_AMOUNT: {TRADE_AMOUNT}")

    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    threading.Thread(target=scan_best_trade).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
