import os
import hmac
import base64
import hashlib
import requests
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

def _signature(timestamp, method, path, body=""):
    msg = f"{timestamp}{method}{path}{body}"
    mac = hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def _headers(timestamp, method, path, body=""):
    return {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": _signature(timestamp, method, path, body),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": API_PASSPHRASE
    }

def place_order(inst_id, side, px, ord_type, sz):
    url = "https://www.okx.com/api/v5/trade/order"
    timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    body = json.dumps({
        "instId": inst_id,
        "tdMode": "cross",
        "side": side,
        "ordType": ord_type,
        "px": px,
        "sz": sz
    })
    return requests.post(url, headers=_headers(timestamp, "POST", "/api/v5/trade/order", body), data=body).json()

def get_account_balance():
    url = "https://www.okx.com/api/v5/account/balance"
    timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    return requests.get(url, headers=_headers(timestamp, "GET", "/api/v5/account/balance")).json()
