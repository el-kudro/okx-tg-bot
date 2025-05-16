import os
import time
import hmac
import base64
import hashlib
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

def _signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def place_order(inst_id, side, px, ord_type, sz):
    url = "https://www.okx.com/api/v5/trade/order"
    timestamp = str(time.time())
    body = {
        "instId": inst_id,
        "tdMode": "cross",
        "side": side,
        "ordType": ord_type,
        "px": px,
        "sz": sz
    }
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": _signature(timestamp, "POST", "/api/v5/trade/order", json.dumps(body)),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": API_PASSPHRASE
    }
    response = requests.post(url, json=body, headers=headers)
    return response.json()