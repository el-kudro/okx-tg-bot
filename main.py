import os
import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from gpt_signal_bot import get_trade_signal
from okx_api import place_order
import threading
import time

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")
TRADE_AMOUNT = os.getenv("TRADE_AMOUNT", "0.01")  # ← подгружаем сумму сделки

bot = telebot.TeleBot(BOT_TOKEN)

last_signals = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я пришлю сигнал, когда будет сильная точка входа. 🧠")

@bot.message_handler(commands=['test'])
def test_signal(message):
    signal = """📈 Сигнал: ЛОНГ по ETH
Вход: 2500
Тейк: 2550
Стоп: 2470
Причина: тестовая сделка для проверки"""

    inst_id = "ETH-USDT"
    last_signals[message.chat.id] = {"inst_id": inst_id, "price": "2500"}

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Войти в сделку по ETH", callback_data="enter_trade_eth"))

    bot.send_message(message.chat.id, signal, reply_markup=markup)

# 📈 Автоматический анализ рынка каждые 30 минут
def auto_market_scan():
    while True:
        coins = ["ETH", "BTC", "SOL"]
        signal_sent = False

        for coin in coins:
            signal = get_trade_signal(coin)
            price = None

            try:
                for line in signal.split("\n"):
                    if "вход" in line.lower():
                        numbers = [s for s in line.split() if s.replace('.', '', 1).isdigit()]
                        if numbers:
                            price = numbers[0]
                            break
            except:
                price = None

            if signal and price:
                inst_id = f"{coin}-USDT"
                last_signals[TELEGRAM_USER_ID] = {"inst_id": inst_id, "price": price}

                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton(f"✅ Войти в сделку по {coin}", callback_data=f"enter_trade_{coin.lower()}"))

                bot.send_message(TELEGRAM_USER_ID, signal, reply_markup=markup)
                signal_sent = True
                break  # Отправляем только один сигнал за цикл

        if not signal_sent:
            bot.send_message(TELEGRAM_USER_ID, "🔍 Подходящий сигнал не обнаружен")

        time.sleep(1800)  # 30 минут

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

# Запускаем фоновый анализ
threading.Thread(target=auto_market_scan).start()

# Запуск Telegram-бота
bot.infinity_polling()
