import os
import re
import time
import requests
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import telebot

# Load environment variables
load_dotenv()

# Initialize bot with retry logic
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
chat_id = -1002300709624

# Configuration
PX_REFERENCE_PRICES = [0.3, 0.2]
START_DATE = datetime(2024, 4, 22, tzinfo=pytz.timezone('Africa/Cairo'))
MONTHLY_PHOTO_URL = "https://i.imgur.com/3iVB3L9.jpg"  # Direct Imgur link
last_monthly_message_date = None
last_price_update = None

def safe_request(url, max_retries=3):
    """Safe request with retries and timeout"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response
        except Exception as e:
            print(f"Request attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    return None

def calculate_percentage_change(current, reference):
    """Safe percentage calculation"""
    try:
        return ((current - reference) / reference) * 100
    except:
        return 0

def format_px_message(price):
    """Formatted PX message with error handling"""
    try:
        message = f"$PX {price:.4f}$\n"
        for ref in PX_REFERENCE_PRICES:
            message += f"From {ref}$ = {calculate_percentage_change(price, ref):+.2f}%\n"
        return message
    except:
        return "$PX Price Unavailable\n"

def format_ton_message(price):
    """Simple TON message"""
    try:
        return f"$TON {price:.2f}$"
    except:
        return "$TON Price Unavailable"

def get_months_since_listing():
    """Arabic month count with timezone awareness"""
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    months = (now.year - START_DATE.year) * 12 + (now.month - START_DATE.month)
    arabic_numbers = {
        1: "الشهر الأول", 2: "الشهر الثاني", 3: "الشهر الثالث",
        4: "الشهر الرابع", 5: "الشهر الخامس", 6: "الشهر السادس",
        7: "الشهر السابع", 8: "الشهر الثامن", 9: "الشهر التاسع",
        10: "الشهر العاشر"
    }
    return arabic_numbers.get(months + 1, f"{months + 1} أشهر")

def generate_monthly_message(price):
    """Monthly message in Arabic with recovery status"""
    months_text = get_months_since_listing()
    recovery = "أخيراً رجعنا الخساره 😍" if price >= PX_REFERENCE_PRICES[0] else "ولسا للأسف مرجعناش الخساره 😢"
    
    return f"""
اه صحيح مبروك يا شباب بقالنا {months_text} من ادراج بكسل
{recovery}

هل لسا عامل هولد ل $PX ؟

لا يعم مشروع تعبان في دماغه - 🔥
اه خلينا نشوف اخره ساشا اي - ❤️
مشاركتش في المشروع اصلا - 😂
"""

def send_with_retry(func, *args, max_retries=3, **kwargs):
    """Retry mechanism for Telegram operations"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Telegram operation failed (attempt {attempt + 1}): {e}")
            time.sleep(5)
    return None

def send_monthly_update(px_price):
    """Send and pin monthly update with photo"""
    global last_monthly_message_date
    
    try:
        # Download photo first to ensure it's available
        photo_data = safe_request(MONTHLY_PHOTO_URL)
        if not photo_data:
            raise Exception("Failed to download photo")
        
        message = generate_monthly_message(px_price)
        sent_msg = send_with_retry(
            bot.send_photo,
            chat_id=chat_id,
            photo=photo_data.content,
            caption=message
        )
        
        if sent_msg:
            send_with_retry(bot.pin_chat_message, chat_id, sent_msg.message_id)
            last_monthly_message_date = datetime.now(pytz.timezone('Africa/Cairo')).date()
    except Exception as e:
        print(f"Monthly update failed: {e}")

def get_coin_prices():
    """Get PX and TON prices with robust parsing"""
    try:
        px_data = safe_request("https://coinmarketcap.com/currencies/not-pixel/")
        ton_data = safe_request("https://coinmarketcap.com/currencies/toncoin/")
        
        if not px_data or not ton_data:
            return None, None
        
        # More reliable price extraction
        px_price = re.search(r'"price":"([\d.]+)"', px_data.text)
        ton_price = re.search(r'"price":"([\d.]+)"', ton_data.text)
        
        return (
            float(px_price.group(1)) if px_price else None,
            float(ton_price.group(1)) if ton_price else None
        )
    except Exception as e:
        print(f"Price fetch error: {e}")
        return None, None

def synchronized_send():
    """Main send logic with timing synchronization"""
    global last_price_update
    
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    px_price, ton_price = get_coin_prices()
    
    # Regular price update
    if px_price and ton_price:
        message = format_px_message(px_price) + "\n" + format_ton_message(ton_price)
        if message != last_price_update:
            send_with_retry(bot.send_message, chat_id, message, parse_mode="Markdown")
            last_price_update = message
    
    # Monthly update check
    if (now.day == 22 and now.hour == 14 and now.minute == 0 and 
        (not last_monthly_message_date or last_monthly_message_date != now.date())):
        if px_price:
            send_monthly_update(px_price)

def main():
    """Main loop with precise timing"""
    while True:
        try:
            # Calculate sleep time to align with :15 second mark
            now = datetime.now(pytz.timezone('Africa/Cairo'))
            next_run = now.replace(second=15, microsecond=0)
            if now >= next_run:
                next_run += timedelta(minutes=1)
            
            sleep_time = (next_run - now).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            synchronized_send()
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
