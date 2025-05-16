import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_trade_signal(symbol="ETH"):
    prompt = f"""
Ты — профессиональный трейдер. Проанализируй {symbol}/USDT и сформируй точку входа в сделку.
Укажи:
- направление (лонг или шорт)
- цену входа
- стоп-лосс
- тейк-профит
- кратко причину
Форматируй как Telegram-сообщение.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Ошибка при запросе сигнала: {e}"
