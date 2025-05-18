import os
import time
import threading
import itertools
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from gpt_signal_bot import get_trade_signal
from okx_api import place_order, get_account_balance

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
coin_cycle = itertools.cycle(["BTC", "ETH", "SOL"])
last_signals = {}

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def receive_webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🤖 Bot is running!\nUse:\n/analyze BTC\n/analyze ETH\n/analyze SOL\n/balance")

@bot.message_handler(commands=['balance'])
def show_balance(message):
    data = get_account_balance()
    try:
        balances = data["data"][0]["details"]
        filtered = [b for b in balances if b["ccy"] in ["USDT", "BTC", "ETH", "SOL"] and float(b["availBal"]) > 0]
        if not filtered:
            bot.send_message(message.chat.id, "Wallet is empty.")
            return
        msg = "💰 Your balances:\n"
        for b in filtered:
            msg += f"{b['ccy']}: {b['availBal']}\n"
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Balance error: {e}")

@bot.message_handler(func=lambda message: message.text.lower().startswith('/analyze '))
def manual_analysis(message):
    parts = message.text.strip().split()
    coin = parts[1].upper() if len(parts) > 1 else None
    if coin not in ["BTC", "ETH", "SOL"]:
        bot.send_message(message.chat.id, "Use: /analyze BTC | ETH | SOL")
        return
    bot.send_message(message.chat.id, f"Analyzing {coin}...")
    signal = get_trade_signal(coin)
    send_signal(message.chat.id, coin, signal)

def send_signal(user_id, coin, signal):
    price = None
    for line in signal.split("\n"):
        if "entry" in line.lower():
            price = ''.join(filter(lambda x: x.isdigit() or x == '.', line))
            break
    if not price:
        price = "market"
    inst_id = f"{coin}-USDT"
    last_signals[user_id] = {"inst_id": inst_id, "price": price}
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(f"✅ Enter trade {coin}", callback_data=f"enter_trade_{coin.lower()}"))
    bot.send_message(user_id, signal, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_trade_"))
def execute_trade(call):
    user_id = call.message.chat.id
    data = last_signals.get(user_id)
    if not data:
        bot.send_message(user_id, "⚠️ Signal not found.")
        return
    inst_id = data["inst_id"]
    price = data["price"]
    result = place_order(inst_id, "buy", price, "market", TRADE_AMOUNT)
    bot.send_message(user_id, f"✅ Order sent: {result}")

def auto_scan():
    while True:
        coin = next(coin_cycle)
        signal = get_trade_signal(coin)
        send_signal(TELEGRAM_USER_ID, coin, signal)
        time.sleep(3600)

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    threading.Thread(target=auto_scan).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
