import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_trade_signal(symbol="ETH"):
    prompt = f"""
    Ты — опытный трейдер. Проанализируй {symbol}/USDT и выбери оптимальную точку входа.
    Верни:
    - направление (лонг или шорт)
    - цену входа
    - тейк-профит
    - стоп-лосс
    - краткую причину

    Формат:
    Сигнал: ЛОНГ по BTC
    Вход: 61250
    Тейк: 62800
    Стоп: 60500
    Причина: RSI < 30 + уровень поддержки + разворотная свеча
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Ошибка анализа {symbol}: {e}"
