import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import telebot

# Load environment variables
load_dotenv()

# Initialize bot
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
chat_id = -1002300709624  # Your chat ID

# PX reference prices
PX_REFERENCE_PRICES = [0.3, 0.2]
START_DATE = datetime(2024, 4, 22)  # Assuming listing was April 22, 2024

def calculate_percentage_change(current_price, reference_price):
    """Calculate percentage change from reference price"""
    return ((current_price - reference_price) / reference_price) * 100

def format_px_message(current_price):
    """Generate formatted message for PX with reference comparisons"""
    message = f"$PX {current_price:.4f}$\n"
    for ref_price in PX_REFERENCE_PRICES:
        percentage = calculate_percentage_change(current_price, ref_price)
        message += f"From {ref_price}$ = {percentage:+.2f}%\n"
    return message

def format_ton_message(current_price):
    """Generate simple message for TON"""
    return f"$TON {current_price:.2f}$"

def get_months_since_listing():
    """Calculate months since listing date in Arabic"""
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    delta = now - START_DATE
    months = delta.days // 30 + 1
    
    arabic_numbers = {
        1: "الشهر الأول",
        2: "الشهر الثاني",
        3: "الشهر الثالث",
        4: "الشهر الرابع",
        5: "الشهر الخامس",
        6: "الشهر السادس",
        7: "الشهر السابع",
        8: "الشهر الثامن",
        9: "الشهر التاسع",
        10: "الشهر العاشر"
    }
    
    return arabic_numbers.get(months, f"{months} أشهر")

def generate_monthly_message(current_price):
    """Generate the monthly status message"""
    months_text = get_months_since_listing()
    initial_price = PX_REFERENCE_PRICES[0]
    current_percentage = calculate_percentage_change(current_price, initial_price)
    
    if current_price >= initial_price:
        recovery_text = "أخيراً رجعنا الخساره 😍"
    else:
        recovery_text = "ولسا للأسف مرجعناش الخساره 😢"
    
    return f"""
اه صحيح مبروك يا شباب بقالنا {months_text} من ادراج بكسل
{recovery_text}

هل لسا عامل هولد ل $PX ؟

لا يعم مشروع تعبان في دماغه - 🔥
اه خلينا نشوف اخره ساشا اي - ❤️
مشاركتش في المشروع اصلا - 😂
"""

def wait_until_next_15_second():
    """Wait until the next :15 second mark"""
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    next_run = now.replace(second=15)
    if now.second >= 15:
        next_run += timedelta(minutes=1)
    wait_seconds = (next_run - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)

def get_coin_prices():
    """Fetch and parse coin prices from CoinMarketCap"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        px = requests.get("https://coinmarketcap.com/currencies/not-pixel/", headers=headers, timeout=10)
        ton = requests.get("https://coinmarketcap.com/currencies/toncoin/", headers=headers, timeout=10)
        
        if px.status_code != 200 or ton.status_code != 200:
            raise Exception("Failed to fetch data")
            
        px_match = re.search(r'"price":"(\d+\.\d+)"', px.text)
        px_price = float(px_match.group(1)) if px_match else None
        
        ton_match = re.search(r'"price":"(\d+\.\d+)"', ton.text)
        ton_price = float(ton_match.group(1)) if ton_match else None
        
        return px_price, ton_price
        
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return None, None

def send_price_update():
    """Send formatted price update to Telegram"""
    px_price, ton_price = get_coin_prices()
    if px_price is None or ton_price is None:
        return
    
    # Regular price message
    message = format_px_message(px_price) + "\n" + format_ton_message(ton_price)
    bot.send_message(chat_id, message, parse_mode="Markdown")
    
    # Monthly message check (22nd at 2 PM Cairo time)
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    if now.day == 22 and now.hour == 14 and now.minute == 0:
        monthly_message = generate_monthly_message(px_price)
        bot.send_message(chat_id, monthly_message)

def main():
    # Initial wait to synchronize with :15 second mark
    wait_until_next_15_second()
    
    while True:
        try:
            send_price_update()
            # Wait until next :15 mark (approximately 60 seconds from now)
            time.sleep(60 - (datetime.now().second % 60) + 15)
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
