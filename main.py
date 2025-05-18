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

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
coin_cycle = itertools.cycle(["BTC", "ETH", "SOL"])
last_signals = {}

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        print(">>> [Webhook] Обновление получено:", update)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"❌ Ошибка обработки Webhook: {e}")
    return "OK", 200

@bot.message_handler(commands=['start'])
def start(message):
    print(">>> [/start] получено")
    bot.send_message(message.chat.id, "✅ Бот активен и слушает через Webhook!\nКоманды: /analyze BTC | ETH | SOL\n/balance")

@bot.message_handler(commands=['balance'])
def show_balance(message):
    data = get_account_balance()
    try:
        if not data or "data" not in data:
            bot.send_message(message.chat.id, f"⚠️ Ошибка OKX: {data.get('msg', 'Unknown error')}")
            return
        balances = data["data"][0]["details"]
        filtered = [b for b in balances if b["ccy"] in ["USDT", "BTC", "ETH", "SOL"] and float(b["availBal"]) > 0]
        if not filtered:
            bot.send_message(message.chat.id, "Пустой кошелек или нет активов.")
            return
        msg = "💰 Баланс:\n"
        for b in filtered:
            msg += f"{b['ccy']}: {b['availBal']}\n"
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка при разборе баланса: {e}")

@bot.message_handler(func=lambda msg: msg.text.lower().startswith("/analyze"))
def analyze(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Формат: /analyze BTC или ETH или SOL")
        return
    coin = parts[1].upper()
    if coin not in ["BTC", "ETH", "SOL"]:
        bot.send_message(message.chat.id, "Разрешено: BTC, ETH, SOL")
        return
    bot.send_message(message.chat.id, f"⏳ Анализ {coin}...")
    signal = get_trade_signal(coin)
    send_signal_to_user(message.chat.id, coin, signal)

def send_signal_to_user(user_id, coin, signal):
    price = None
    probability = "?"
    try:
        for line in signal.split("\n"):
            if "entry" in line.lower() or "вход" in line.lower():
                numbers = [s for s in line.split() if s.replace('.', '', 1).isdigit()]
                if numbers:
                    price = numbers[0]
            if "%" in line or "probab" in line.lower():
                probability = line.strip()
    except:
        price = None

    if signal and price:
        inst_id = f"{coin}-USDT"
        last_signals[user_id] = {"inst_id": inst_id, "price": price}
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✅ Войти в сделку по {coin}", callback_data=f"enter_trade_{coin.lower()}"))
        bot.send_message(user_id, f"{signal}\n\n📊 Вероятность: {probability}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_trade_"))
def execute_trade(call):
    user_id = call.message.chat.id
    data = last_signals.get(user_id)
    if not data:
        bot.send_message(user_id, "⚠️ Сигнал не найден.")
        return
    inst_id = data["inst_id"]
    price = data["price"] or "market"
    response = place_order(inst_id=inst_id, side="buy", px=price, ord_type="market", sz=TRADE_AMOUNT)
    bot.send_message(user_id, f"✅ Ордер отправлен в {inst_id}:\n{response}")

if __name__ == "__main__":
    print(">>> Установка Webhook...")
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
