import os
import openai
import telebot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID")

bot = telebot.TeleBot(BOT_TOKEN)
openai.api_key = OPENAI_API_KEY

@bot.message_handler(commands=["анализ"])
def analyze_market(message):
    bot.send_message(message.chat.id, "⏳ Анализирую рынок, подожди 5–10 секунд...")

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты профессиональный криптотрейдер. Выбери сам одну самую ликвидную пару, "
                        "проанализируй график (уровни, свечи, RSI, объем), и пришли короткий, но точный сигнал. "
                        "Укажи вход, стоп, тейк, RR и причину. Отвечай строго как трейдинг-бот, без вступлений."
                    )
                },
                {
                    "role": "user",
                    "content": "Проанализируй рынок и пришли одну наилучшую точку входа в сделку с минимальным риском."
                }
            ]
        )

        signal = completion.choices[0].message.content.strip()
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("✅ Войти в сделку", callback_data="enter_trade"))
        bot.send_message(message.chat.id, signal, reply_markup=markup)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при анализе рынка: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "enter_trade")
def execute_trade(call):
    # заглушка — можно подключить функцию place_order
    bot.send_message(call.message.chat.id, "🛠 Ордер будет отправлен (реализация в main.py)")
