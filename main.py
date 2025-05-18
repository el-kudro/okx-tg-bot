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
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

print(f"BOT_TOKEN: {BOT_TOKEN}")
print(f"WEBHOOK_URL: {WEBHOOK_URL}")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
coin_cycle = itertools.cycle(["BTC", "ETH", "SOL"])
last_signals = {}

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"Webhook error: {e}")
    return "OK", 200

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🤖 Bot is active. Use /analyze BTC, /balance etc.")

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
        msg = "💰 Current balance:\n" + "\n".join(f"{b['ccy']}: {b['availBal']}" for b in filtered)
        bot.send_message(message.chat.id, msg)
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {e}")

@bot.message_handler(func=lambda message: message.text.lower().startswith('/analyze '))
def manual_analysis(message):
    coin = message.text.strip().split()[1].upper()
    if coin not in ["BTC", "ETH", "SOL"]:
        bot.send_message(message.chat.id, "Allowed: BTC, ETH, SOL")
        return
    signal = get_trade_signal(coin)
    send_signal_to_user(message.chat.id, coin, signal)

def send_signal_to_user(user_id, coin, signal):
    price = None
    for line in signal.split("\n"):
        if "entry" in line.lower() or "вход" in line.lower():
            nums = [s for s in line.split() if s.replace('.', '', 1).isdigit()]
            if nums:
                price = nums[0]
                break
    if signal and price:
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
    response = place_order(data["inst_id"], "buy", data["price"] or "market", "market", TRADE_AMOUNT)
    bot.send_message(user_id, f"✅ Order sent: {response}")

def auto_market_scan():
    while True:
        coin = next(coin_cycle)
        now = datetime.now().time()
        signal = get_trade_signal(coin)
        prob = 0
        for line in signal.split("\n"):
            if "%" in line:
                digits = ''.join([c for c in line if c.isdigit()])
                try: prob = int(digits)
                except: pass
                break
        if datetime.strptime("10:00", "%H:%M").time() <= now <= datetime.strptime("23:00", "%H:%M").time():
            if prob >= 90:
                send_signal_to_user(TELEGRAM_USER_ID, coin, signal)
        else:
            send_signal_to_user(TELEGRAM_USER_ID, coin, signal)
        time.sleep(3600)

if __name__ == "__main__":
    success = bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    print(f"Webhook set: {success}")
    threading.Thread(target=auto_market_scan).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
