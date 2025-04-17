import os
import re
import time
import requests
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import telebot
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize bot with timeout
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
chat_id = -1002300709624

# Configuration
PX_REFERENCE_PRICES = [0.3, 0.2]
START_DATE = datetime(2024, 4, 22, tzinfo=pytz.timezone('Africa/Cairo'))
MONTHLY_PHOTO_URL = "https://i.imgur.com/3iVB3L9.jpg"
last_monthly_message_date = None
last_price_update = None

def safe_request(url, max_retries=3):
    """Safe request with retries and timeout"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    for attempt in range(max_retries):
        try:
            logger.info(f"Making request to {url} (attempt {attempt + 1})")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                logger.info("Request successful")
                return response
            logger.warning(f"Request failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
        time.sleep(5)
    return None

def send_telegram_message(text, photo_url=None):
    """Send message to Telegram with error handling"""
    try:
        logger.info(f"Attempting to send message: {text[:50]}...")
        if photo_url:
            response = safe_request(photo_url)
            if response:
                sent_msg = bot.send_photo(chat_id, response.content, caption=text)
                logger.info("Photo message sent successfully")
                return sent_msg
        else:
            sent_msg = bot.send_message(chat_id, text, parse_mode="Markdown")
            logger.info("Text message sent successfully")
            return sent_msg
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")
    return None

def get_coin_prices():
    """Get current coin prices with robust error handling"""
    logger.info("Fetching coin prices...")
    try:
        px_data = safe_request("https://coinmarketcap.com/currencies/not-pixel/")
        ton_data = safe_request("https://coinmarketcap.com/currencies/toncoin/")
        
        if not px_data or not ton_data:
            logger.warning("Failed to fetch one or both coin prices")
            return None, None
        
        px_match = re.search(r'"price":"([\d.]+)"', px_data.text)
        ton_match = re.search(r'"price":"([\d.]+)"', ton_data.text)
        
        px_price = float(px_match.group(1)) if px_match else None
        ton_price = float(ton_match.group(1)) if ton_match else None
        
        logger.info(f"Fetched prices - PX: {px_price}, TON: {ton_price}")
        return px_price, ton_price
        
    except Exception as e:
        logger.error(f"Error in get_coin_prices: {str(e)}")
        return None, None

def send_price_update():
    """Send regular price update"""
    global last_price_update
    
    px_price, ton_price = get_coin_prices()
    if px_price is None or ton_price is None:
        logger.warning("Skipping price update due to missing data")
        return
    
    message = f"$PX {px_price:.4f}$\n"
    for ref in PX_REFERENCE_PRICES:
        change = ((px_price - ref) / ref) * 100
        message += f"From {ref}$ = {change:+.2f}%\n"
    message += f"\n$TON {ton_price:.2f}$"
    
    if message != last_price_update:
        if send_telegram_message(message):
            last_price_update = message
            logger.info("Price update sent successfully")
        else:
            logger.error("Failed to send price update")

def send_monthly_update():
    """Send monthly update with photo"""
    global last_monthly_message_date
    
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    px_price, _ = get_coin_prices()
    
    if px_price is None:
        logger.error("Cannot send monthly update without PX price")
        return
    
    months = (now.year - START_DATE.year) * 12 + (now.month - START_DATE.month)
    arabic_months = [
        "الشهر الأول", "الشهر الثاني", "الشهر الثالث",
        "الشهر الرابع", "الشهر الخامس", "الشهر السادس",
        "الشهر السابع", "الشهر الثامن", "الشهر التاسع",
        "الشهر العاشر"
    ]
    month_text = arabic_months[months] if months < len(arabic_months) else f"{months + 1} أشهر"
    
    recovery = "أخيراً رجعنا الخساره 😍" if px_price >= PX_REFERENCE_PRICES[0] else "ولسا للأسف مرجعناش الخساره 😢"
    
    message = f"""
اه صحيح مبروك يا شباب بقالنا {month_text} من ادراج بكسل
{recovery}

هل لسا عامل هولد ل $PX ؟

لا يعم مشروع تعبان في دماغه - 🔥
اه خلينا نشوف اخره ساشا اي - ❤️
مشاركتش في المشروع اصلا - 😂
"""
    
    sent_msg = send_telegram_message(message, MONTHLY_PHOTO_URL)
    if sent_msg:
        try:
            bot.pin_chat_message(chat_id, sent_msg.message_id)
            last_monthly_message_date = now.date()
            logger.info("Monthly update sent and pinned successfully")
        except Exception as e:
            logger.error(f"Failed to pin message: {str(e)}")

def main():
    logger.info("Starting Telegram price bot...")
    
    # Initial connection test
    try:
        bot.get_me()
        logger.info("Bot connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Telegram: {str(e)}")
        return
    
    while True:
        try:
            now = datetime.now(pytz.timezone('Africa/Cairo'))
            logger.info(f"Current Cairo time: {now}")
            
            # Check if it's time for monthly update
            if (now.day == 22 and now.hour == 14 and now.minute == 0 and 
                (last_monthly_message_date is None or last_monthly_message_date != now.date())):
                logger.info("Time for monthly update")
                send_monthly_update()
            
            # Regular price updates at :15 of each minute
            if now.second == 15:
                logger.info("Time for regular price update")
                send_price_update()
            
            # Sleep until next second
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()
