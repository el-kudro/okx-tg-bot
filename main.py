import os
import telebot
from dotenv import load_dotenv
from gpt_signal_bot import get_trade_signal

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я готов анализировать рынок. Напиши /анализ")

@bot.message_handler(commands=['анализ'])
def analyze_market(message):
    bot.send_message(message.chat.id, "🔍 Анализирую рынок, подожди пару секунд...")
    signal = get_trade_signal("ETH")  # Можно заменить на BTC, SOL и т.д.
    bot.send_message(message.chat.id, signal)

bot.infinity_polling()
