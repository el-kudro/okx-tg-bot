import os
import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from gpt_signal_bot import get_trade_signal
from okx_api import place_order
import threading
import time
import itertools

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")

bot = telebot.TeleBot(BOT_TOKEN)
last_signals = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я присылаю сигналы каждый час. Также можешь запросить вручную:\n/анализ BTC\n/анализ ETH\n/анализ SOL")

# 🔁 Монеты по очереди для автоматического анализа
coin_cycle = itertools.cycle(["BTC", "ETH", "SOL"])

def send_signal_to_user(user_id, coin, signal):
    price = None
    probability = "?"

    try:
        for line in signal.split("\n"):
            if "вход" in line.lower():
                numbers = [s for s in line.split() if s.replace('.', '', 1).isdigit()]
                if numbers:
                    price = numbers[0]
            if "вероятност" in line.lower() or "%" in line:
                probability = line.strip()
    except:
        price = None

    if signal and price:
        inst_id = f"{coin}-USDT"
        last_signals[user_id] = {"inst_id": inst_id, "price": price}

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"✅ Войти в сделку по {coin}", callback_data=f"enter_trade_{coin.lower()}"))

        full_signal = f"{signal}\n\n📊 {probability if '%' in probability else 'Вероятность успеха: ~70%'}"
        bot.send_message(user_id, full_signal, reply_markup=markup)

# ✅ Ручной анализ
@bot.message_handler(func=lambda message: message.text.lower().startswith('/анализ '))
def manual_analysis(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Напиши так: /анализ BTC или ETH или SOL")
        return

    coin = parts[1].upper()
    if coin not in ["BTC", "ETH", "SOL"]:
        bot.send_message(message.chat.id, "Допустимые монеты: BTC, ETH, SOL")
        return

    bot.send_message(message.chat.id, f"Запрашиваю анализ по {coin}...")
    signal = get_trade_signal(coin)
    send_signal_to_user(message.chat.id, coin, signal)

# ✅ Автоматический анализ каждый час
def auto_market_scan():
    while True:
        coin = next(coin_cycle)
        signal = get_trade_signal(coin)
        send_signal_to_user(TELEGRAM_USER_ID, coin, signal)
        time.sleep(3600)

# ✅ Обработка кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith("enter_trade_"))
def execute_trade(call):
    user_id = call.message.chat.id
    data = last_signals.get(user_id)

    if not data:
        bot.send_message(call.message.chat.id, "⚠️ Не найден сигнал.")
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

    bot.send_message(call.message.chat.id, f"✅ Ордер отправлен по {inst_id}: {response}")

# 🔁 Запуск автоанализа
threading.Thread(target=auto_market_scan).start()

# ▶️ Запуск Telegram-бота
bot.infinity_polling()
