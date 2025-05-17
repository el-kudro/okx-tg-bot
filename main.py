import os
import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from gpt_signal_bot import get_trade_signal
from okx_api import place_order, get_account_balance
import threading
import time
import itertools
from datetime import datetime

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")

bot = telebot.TeleBot(BOT_TOKEN)
last_signals = {}
coin_cycle = itertools.cycle(["BTC", "ETH", "SOL"])

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Hello! I send signals every hour (currently every 30 sec for testing).\nCommands:\n/analyze BTC\n/analyze ETH\n/analyze SOL\n/balance")

@bot.message_handler(func=lambda message: message.text.lower().startswith('/analyze '))
def manual_analysis(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Use: /analyze BTC or ETH or SOL")
        return

    coin = parts[1].upper()
    if coin not in ["BTC", "ETH", "SOL"]:
        bot.send_message(message.chat.id, "Allowed coins: BTC, ETH, SOL")
        return

    bot.send_message(message.chat.id, f"Analyzing {coin}...")
    signal = get_trade_signal(coin)
    send_signal_to_user(message.chat.id, coin, signal)

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

def send_signal_to_user(user_id, coin, signal):
    price = None
    probability_line = "?"
    probability_value = 0

    try:
        for line in signal.split("\n"):
            if "вход" in line.lower() or "entry" in line.lower():
                numbers = [s for s in line.split() if s.replace('.', '', 1).isdigit()]
                if numbers:
                    price = numbers[0]
            if "%" in line or "probab" in line.lower() or "вероят" in line.lower():
                probability_line = line.strip()
                digits = ''.join([c for c in line if c.isdigit()])
                try:
                    probability_value = int(digits)
                except:
                    probability_value = 0
    except:
        price = None

    if signal and price:
        inst_id = f"{coin}-USDT"
        last_signals[user_id] = {"inst_id": inst_id, "price": price}

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✅ Enter trade {coin}", callback_data=f"enter_trade_{coin.lower()}"))

        full_signal = f"{signal}\n\n📊 {probability_line if '%' in probability_line else 'Success probability: ~70%'}"
        bot.send_message(user_id, full_signal, reply_markup=markup)

def auto_market_scan():
    while True:
        coin = next(coin_cycle)
        now = datetime.now().time()
        signal = get_trade_signal(coin)

        # Извлекаем вероятность
        probability = 0
        for line in signal.split("\n"):
            if "%" in line:
                digits = ''.join([c for c in line if c.isdigit()])
                try:
                    probability = int(digits)
                except:
                    probability = 0
                break

        # Проверка по времени (10:00–23:00)
        restricted_start = datetime.strptime("10:00", "%H:%M").time()
        restricted_end = datetime.strptime("23:00", "%H:%M").time()

        if restricted_start <= now <= restricted_end:
            if probability >= 90:
                send_signal_to_user(TELEGRAM_USER_ID, coin, signal)
                print(f"✅ [HIGH PROB] {coin} | {probability}% sent")
            else:
                print(f"⏸ {coin} skipped ({probability}%) during restricted hours")
        else:
            send_signal_to_user(TELEGRAM_USER_ID, coin, signal)
            print(f"✅ [NIGHT] {coin} | {probability}% sent")

        time.sleep(30)  # ← заменить на 3600 после тестов

@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_trade_"))
def execute_trade(call):
    user_id = call.message.chat.id
    data = last_signals.get(user_id)

    if not data:
        bot.send_message(call.message.chat.id, "⚠️ Signal not found.")
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

    bot.send_message(call.message.chat.id, f"✅ Order sent to {inst_id}: {response}")

# Start scanning in background
threading.Thread(target=auto_market_scan).start()
try:
    bot.infinity_polling()
except Exception as e:
    print(f"❌ Telegram polling error: {e}")
