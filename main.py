import os
import requests
import re
import json
import time
import telebot
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the bot with environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Missing Telegram Bot Token or Chat ID in environment variables")

bot = telebot.TeleBot(BOT_TOKEN)
chat_id = int(CHAT_ID)  # Ensure CHAT_ID is an integer

# Reference prices for $PX
previous_prices = {
    'high': 0.3,
    'low': 0.2
}

def calculate_loss_percentage(initial_price, current_price):
    loss = initial_price - current_price
    percentage = (loss / initial_price) * 100
    # Ensure it shows "-" when the price is lower than the starting price
    return f"-{abs(percentage):.2f}%" if current_price < initial_price else f"+{percentage:.2f}%"

def format_price(price, coin_name):
    if coin_name == "px":
        return "{:.4f}".format(price)  # Forces 4 decimal digits (e.g., 0.0710)
    elif coin_name == "ton":
        return round(price, 2)  # TON remains at 2 decimal digits
    return round(price)

def get_prices():
    try:
        cmc_home = requests.get("https://coinmarketcap.com/", timeout=10)
        px_page = requests.get("https://coinmarketcap.com/currencies/not-pixel/", timeout=10)
        ton_page = requests.get("https://coinmarketcap.com/currencies/toncoin/", timeout=10)

        if cmc_home.status_code != 200 or px_page.status_code != 200 or ton_page.status_code != 200:
            print("Failed to retrieve data")
            return None, None

        # Parse trending coins from homepage
        trending_match = re.search(r'"highlightsData":\{"trendingList":(\[.*?\])', cmc_home.text)
        if trending_match:
            try:
                trending_list = json.loads(trending_match.group(1))
                for coin in trending_list:
                    name = coin.get("name", "").replace(" ", "_").lower()
                    price = coin.get("priceChange", {}).get("price")
                    if price:
                        globals()[name] = float(price)
            except Exception as e:
                print(f"Error parsing trending list: {e}")
        else:
            print("Trending list not found")

        # Parse TON price
        ton_match = re.search(r'"statistics":(\{.*?\})', ton_page.text)
        ton_price = None
        if ton_match:
            try:
                ton_stats = json.loads(ton_match.group(1))
                ton_price = float(ton_stats.get("price", 0))
            except Exception as e:
                print(f"TON JSON error: {e}")

        # Parse PX price
        px_match = re.search(r'"statistics":(\{.*?\})', px_page.text)
        px_price = None
        if px_match:
            try:
                px_stats = json.loads(px_match.group(1))
                px_price = float(px_stats.get("price", 0))
            except Exception as e:
                print(f"PX JSON error: {e}")

        return px_price, ton_price

    except Exception as e:
        print(f"General error: {e}")
        return None, None

def send_price_update():
    px_price, ton_price = get_prices()
    if px_price and ton_price:
        loss_high = calculate_loss_percentage(previous_prices['high'], px_price)
        loss_low = calculate_loss_percentage(previous_prices['low'], px_price)

        message_text = f"""
$PX {format_price(px_price, 'px')}$  
From 0.3$ = {loss_high} 
From 0.2$ = {loss_low}

$TON {format_price(ton_price, 'ton')}$ 
"""
        bot.send_message(chat_id=chat_id, text=message_text.strip(), parse_mode="Markdown")

while True:
    now = datetime.now()
    if now.second == 15:  # Check if current second is 15
        send_price_update()
        time.sleep(1)  # Avoid sending multiple times in the same second
    time.sleep(0.1)  # Small delay to reduce CPU usage
