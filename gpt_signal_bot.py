import os
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_trade_signal(symbol="ETH"):
    prompt = f"""
    You are a professional crypto trader. Analyze {symbol}/USDT and generate a signal with:

    - Direction: LONG or SHORT
    - Entry price
    - Take profit
    - Stop loss
    - Short reason (RSI, support/resistance, candles, etc.)
    - Success probability (in %)

    Format:

    Signal: LONG on {symbol}  
    Entry: 2380  
    Take Profit: 2450  
    Stop Loss: 2345  
    Reason: RSI < 30 + strong support + bullish engulfing  
    Probability: 84%
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        content = response["choices"][0]["message"]["content"]
        print(f"✅ GPT-3.5 Response for {symbol}:\n{content}")
        return content
    except Exception as e:
        print(f"❌ GPT-3.5 Error: {e}")
        return ""
