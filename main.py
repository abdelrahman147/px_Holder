import os
import re
import time
import requests
from datetime import datetime
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

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
chat_id = -1002300709624  # Replace with your target group/chat ID

# Configuration
PX_REFERENCE_PRICES = [0.3, 0.2]
START_DATE = datetime(2024, 4, 22, tzinfo=pytz.timezone('Africa/Cairo'))
MONTHLY_PHOTO_URL = "https://i.imgur.com/3iVB3L9.jpg"
last_monthly_message_date = None
last_price_update = None

def safe_request(url, max_retries=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    for attempt in range(max_retries):
        try:
            logger.info(f"Requesting: {url} (attempt {attempt + 1})")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response
            logger.warning(f"Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
        time.sleep(5)
    return None

def send_telegram_message(text, photo_url=None):
    try:
        logger.info("Sending Telegram message...")
        if photo_url:
            photo_resp = safe_request(photo_url)
            if photo_resp:
                msg = bot.send_photo(chat_id, photo_resp.content, caption=text)
                logger.info("Photo message sent")
                return msg
        else:
            msg = bot.send_message(chat_id, text, parse_mode="Markdown")
            logger.info("Text message sent")
            return msg
    except Exception as e:
        logger.error(f"Telegram error: {str(e)}")
    return None

def get_coin_prices():
    logger.info("Fetching coin prices...")
    try:
        px_data = safe_request("https://coinmarketcap.com/currencies/not-pixel/")
        ton_data = safe_request("https://coinmarketcap.com/currencies/toncoin/")
        
        if not px_data or not ton_data:
            logger.warning("Missing data from CoinMarketCap")
            return None, None
        
        # Improved regex to extract prices (handles commas)
        px_match = re.search(r'"price"\s*:\s*"([\d,\.]+)"', px_data.text)
        ton_match = re.search(r'"price"\s*:\s*"([\d,\.]+)"', ton_data.text)

        px_price = float(px_match.group(1).replace(',', '')) if px_match else None
        ton_price = float(ton_match.group(1).replace(',', '')) if ton_match else None
        
        logger.info(f"Prices -> PX: {px_price}, TON: {ton_price}")
        return px_price, ton_price
    except Exception as e:
        logger.error(f"Price fetch error: {str(e)}")
        return None, None

def send_price_update():
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
            logger.info("Price update sent")
        else:
            logger.error("Failed to send price update")

def send_monthly_update():
    global last_monthly_message_date
    
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    px_price, _ = get_coin_prices()
    if px_price is None:
        logger.error("Missing PX price for monthly update")
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
            # Optional: unpin previous message (prevent clutter)
            try:
                pinned = bot.get_chat(chat_id).pinned_message
                if pinned:
                    bot.unpin_chat_message(chat_id, pinned.message_id)
                    logger.info("Unpinned previous message")
            except Exception as e:
                logger.warning(f"Unpin failed: {str(e)}")

            bot.pin_chat_message(chat_id, sent_msg.message_id)
            last_monthly_message_date = now.date()
            logger.info("Monthly message pinned")
        except Exception as e:
            logger.error(f"Pinning error: {str(e)}")

def main():
    logger.info("Starting price bot...")
    try:
        bot.get_me()
        logger.info("Bot is connected to Telegram")
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        return
    
    while True:
        try:
            now = datetime.now(pytz.timezone('Africa/Cairo'))
            logger.info(f"Cairo time: {now.strftime('%Y-%m-%d %H:%M:%S')}")

            # Monthly update on 22nd @ 14:00
            if (now.day == 22 and now.hour == 14 and now.minute == 0 and 
                (last_monthly_message_date is None or last_monthly_message_date != now.date())):
                send_monthly_update()
            
            # Price update at every minute when second == 15
            if now.second == 15:
                send_price_update()
            
            time.sleep(1)
        except Exception as e:
            logger.error(f"Main loop error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()
