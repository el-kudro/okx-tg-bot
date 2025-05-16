import os
import telebot
from okx_api import place_order
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я твой трейдинг-бот. Жди сигналов! 🚀")

@bot.message_handler(commands=['signal'])
def send_signal(message):
    signal_text = (
        "📈 Сигнал: ЛОНГ по ETH/USDT\n"
        "Цена входа: 2490\n"
        "Стоп-лосс: 2465\n"
        "Тейк-профит: 2540"
    )
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("✅ Войти в сделку", callback_data="enter_trade"))
    bot.send_message(message.chat.id, signal_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "enter_trade")
def callback_enter_trade(call):
    response = place_order("ETH-USDT", "buy", "2490", "market", "0.01")
    bot.send_message(call.message.chat.id, f"Ордер отправлен: {response}")

bot.infinity_polling()