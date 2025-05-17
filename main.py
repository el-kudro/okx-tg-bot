import os
from flask import Flask, request
import telebot
from dotenv import load_dotenv
from gpt_signal_bot import get_trade_signal
from okx_api import place_order, get_account_balance
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
last_signals = {}

@app.route(f"/{BOT_TOKEN}", methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🚀 Bot is active via Webhook. Use /analyze, /balance.")

@bot.message_handler(commands=['analyze'])
def analyze(message):
    coin = "ETH"
    signal = get_trade_signal(coin)
    if signal:
        last_signals[message.chat.id] = {"inst_id": f"{coin}-USDT", "price": extract_entry_price(signal)}
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✅ Enter {coin}", callback_data="enter_trade"))
        bot.send_message(message.chat.id, signal, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⚠️ No signal generated.")

@bot.message_handler(commands=['balance'])
def balance(message):
    data = get_account_balance()
    try:
        balances = data.get("data", [])[0].get("details", [])
        filtered = [b for b in balances if float(b.get("availBal", 0)) > 0]
        msg = "💰 Balance:\n" + "\n".join(f"{b['ccy']}: {b['availBal']}" for b in filtered)
        bot.send_message(message.chat.id, msg or "Empty wallet.")
    except:
        bot.send_message(message.chat.id, "⚠️ Balance error.")

@bot.callback_query_handler(func=lambda call: call.data == "enter_trade")
def execute_trade(call):
    data = last_signals.get(call.message.chat.id)
    if not data:
        bot.send_message(call.message.chat.id, "⚠️ Signal not found.")
        return
    response = place_order(data["inst_id"], "buy", data["price"], "market", TRADE_AMOUNT)
    bot.send_message(call.message.chat.id, f"✅ Order sent: {response}")

def extract_entry_price(text):
    for line in text.split("\n"):
        if "entry" in line.lower() or "вход" in line.lower():
            for word in line.split():
                if word.replace(".", "", 1).isdigit():
                    return word
    return "market"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
