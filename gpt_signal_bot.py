import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_trade_signal(symbol="ETH"):
    prompt = f"""
    You are a professional crypto trader. Analyze {symbol}/USDT and return:
    - Signal (LONG/SHORT)
    - Entry
    - Take profit
    - Stop loss
    - Short reason
    - Success probability (in %)

    Format:
    Signal: LONG on {symbol}
    Entry: 2450
    Take Profit: 2550
    Stop Loss: 2390
    Reason: Support + RSI oversold
    Probability: 82%
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ GPT error: {e}")
        return ""
