import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_trade_signal(symbol="ETH"):
    prompt = f"""
    You are a professional crypto trader. Analyze {symbol}/USDT and return:
    - Signal: LONG or SHORT
    - Entry
    - Take Profit
    - Stop Loss
    - Reason
    - Probability (%)
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ GPT error: {e}"
