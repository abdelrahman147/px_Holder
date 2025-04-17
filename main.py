import os
import re
import json
import time
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv
import telebot

# Load environment variables
load_dotenv()

# Initialize bot with token from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
chat_id = -1002300709624  # Your chat ID
previous_price = 0.3  # Initial price reference

# Track monthly message status
last_monthly_message_sent = None

def calculate_loss_percentage(initial_price, current_price):
    """Calculate percentage loss from initial price"""
    loss = initial_price - current_price
    return (loss / initial_price) * 100

def format_price(price, coin_name):
    """Format price based on coin type"""
    if coin_name == "px":
        return round(price, 4)
    elif coin_name == "ton":
        return round(price, 2)
    return int(price)

def get_monthly_message_data():
    """Generate monthly message text in Arabic"""
    arabic_numbers = {
        1: "الأول",
        2: "الثاني", 
        3: "الثالث",
        4: "الرابع",
        5: "الخامس",
        6: "السادس",
        7: "السابع",
        8: "الثامن",
        9: "التاسع",
        10: "العاشر"
    }
    
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    months_since_start = (now.year - 2024) * 12 + now.month - 4  # Starting from April 2024
    month_text = arabic_numbers.get(months_since_start, str(months_since_start))
    
    return month_text

def check_and_send_monthly_message(current_price):
    """Check if monthly message should be sent"""
    global last_monthly_message_sent
    
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    today = now.date()
    
    # Check if it's the 22nd between 2:00-2:01 PM Cairo time
    if (now.day == 22 and 
        now.hour == 14 and 
        now.minute == 0 and
        (last_monthly_message_sent != today)):
        
        loss_percentage = calculate_loss_percentage(previous_price, current_price)
        month_text = get_monthly_message_data()
        
        message = f"""
مبروك يا شباب بقالكم عاملين هولد لبكسل {month_text} والان علي خساره {loss_percentage:.2f}%
"""
        bot.send_message(chat_id, message)
        last_monthly_message_sent = today

def fetch_coin_data():
    """Fetch data from CoinMarketCap"""
    try:
        s = requests.get("https://coinmarketcap.com/", timeout=10)
        px = requests.get("https://coinmarketcap.com/currencies/not-pixel/", timeout=10)
        ton = requests.get("https://coinmarketcap.com/currencies/toncoin/", timeout=10)
        
        if s.status_code != 200 or px.status_code != 200 or ton.status_code != 200:
            raise Exception("Failed to fetch data from CoinMarketCap")
            
        return s.text, px.text, ton.text
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None, None

def parse_coin_data(data, cd, cd2):
    """Parse the HTML data to extract coin prices"""
    coins = {}
    
    # Parse trending coins
    match = re.search(r'"highlightsData":\{"trendingList":(\[.*?\])', data)
    if match:
        try:
            trending_list = json.loads(match.group(1))
            for coin in trending_list:
                name = coin.get("name", "").replace(" ", "_").lower()
                price = coin.get("priceChange", {}).get("price", 0)
                coins[name] = price
        except json.JSONDecodeError:
            print("Error parsing trending list")

    # Parse TON coin
    match = re.search(r'"statistics":(\{.*?\})', cd2)
    if match:
        try:
            stats = json.loads(match.group(1))
            coins['toncoin'] = stats.get("price", 0)
        except json.JSONDecodeError:
            print("Error parsing TON stats")

    # Parse PIXEL coin
    match = re.search(r'"statistics":(\{.*?\})', cd)
    if match:
        try:
            stats = json.loads(match.group(1))
            coins['not_pixel'] = stats.get("price", 0)
        except json.JSONDecodeError:
            print("Error parsing PIXEL stats")

    return coins

def main():
    while True:
        try:
            # Get current Cairo time
            now = datetime.now(pytz.timezone('Africa/Cairo'))
            
            # Fetch and parse data
            data, px_data, ton_data = fetch_coin_data()
            if not all([data, px_data, ton_data]):
                time.sleep(60)
                continue
                
            coins = parse_coin_data(data, px_data, ton_data)
            
            # Prepare and send message
            if 'not_pixel' in coins and 'toncoin' in coins:
                px_price = float(coins['not_pixel'])
                ton_price = float(coins['toncoin'])
                
                loss_percentage = calculate_loss_percentage(previous_price, px_price)
                
                # Format prices
                formatted_px = format_price(px_price, "px")
                formatted_ton = format_price(ton_price, "ton")
                
                # Send regular update
                message = f"""
$PX {formatted_px}$  |  -{loss_percentage:.2f}%

$TON {formatted_ton}$ 
"""
                bot.send_message(chat_id, message, parse_mode="Markdown")
                
                # Check for monthly message
                check_and_send_monthly_message(px_price)
            
            # Sleep for 1 minute before next check
            time.sleep(60)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
