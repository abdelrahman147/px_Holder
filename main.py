import requests
import re
import json
import time
import telebot
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
chat_id = -1002300709624
previous_price = 0.3

# Track the month count for the congratulatory message
month_count = 0
last_month_sent = 0

def calculate_loss_percentage(initial_price, current_price):
    loss = initial_price - current_price
    loss_percentage = (loss / initial_price) * 100
    return loss_percentage

def format_price(price, coin_name):
    if coin_name == "px": 
        return round(price, 4) 
    elif coin_name == "ton": 
        return round(price, 2) 
    else:
        return int(price)  

def get_month_count():
    global month_count, last_month_sent
    now = datetime.now(pytz.timezone('Africa/Cairo'))
    today = now.day
    current_month = now.month
    
    # If it's the 22nd and we haven't sent the message this month
    if today == 22 and current_month != last_month_sent:
        # Calculate how many months since the first message
        first_message_date = datetime(2024, 4, 22)  # Assuming first message was April 22, 2024
        delta = now - first_message_date
        month_count = delta.days // 30 + 1  # Approximate month count
        last_month_sent = current_month
        return month_count
    return 0

def send_monthly_message(loss_percentage):
    month_count = get_month_count()
    if month_count > 0:
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
            10: "العاشر",
            # Add more as needed
        }
        
        month_text = arabic_numbers.get(month_count, f"{month_count}")
        message = f"""
مبروك يا شباب بقالكم عاملين هولد لبكسل {month_text} والان علي خساره {loss_percentage:.2f}%
"""
        bot.send_message(chat_id=chat_id, text=message)

while True:
    # Get current time in Egypt timezone
    egypt_tz = pytz.timezone('Africa/Cairo')
    now = datetime.now(egypt_tz)
    
    s = requests.get("https://coinmarketcap.com/", timeout=10)
    px = requests.get("https://coinmarketcap.com/currencies/not-pixel/", timeout=10)
    ton = requests.get("https://coinmarketcap.com/currencies/toncoin/", timeout=10)

    if s.status_code != 200 or px.status_code != 200 or ton.status_code != 200:
        print("Failed to retrieve data")
        time.sleep(60)
        continue

    data = s.text
    cd = px.text
    cd2 = ton.text

    match = re.search(r'"highlightsData":\{"trendingList":(\[.*?\])', data)

    if match:
        try:
            trending_list = json.loads(match.group(1))
            for coin in trending_list:
                name = coin.get("name", "Unknown Coin").replace(" ", "_").lower()
                price = coin.get("priceChange", {}).get("price", "N/A")
                globals()[name] = price  
        except json.JSONDecodeError:
            print("Error parsing trending list JSON")
    else:
        print("Highlights data not found.")

    match = re.search(r'"statistics":(\{.*?\})', cd2)
    name_match = re.search(r'"name":"(.*?)"', cd2)

    if match:
        try:
            statistics_json = match.group(1)
            statistics_dict = json.loads(statistics_json)
            price = statistics_dict.get("price", "N/A")
            coin_name = name_match.group(1).replace(" ", "_").lower() if name_match else "unknown_coin"  
            globals()[coin_name] = price
            x = price

        except json.JSONDecodeError:
            print("Error parsing statistics JSON")

    match = re.search(r'"statistics":(\{.*?\})', cd)
    name_match = re.search(r'"name":"(.*?)"', cd)

    if match:
        try:
            statistics_json = match.group(1)
            statistics_dict = json.loads(statistics_json)
            price = statistics_dict.get("price", "N/A")
            coin_name = name_match.group(1).replace(" ", "_").lower() if name_match else "unknown_coin"  
            globals()[coin_name] = price 

            if price != "N/A" and price != 0:
                try:
                    loss_percentage = ((previous_price - float(price)) / previous_price) * 100
                    print(f"{coin_name.capitalize()} - Loss Percentage: {loss_percentage:.2f}%")
                    
                    # Check if we need to send the monthly message
                    if now.day == 22 and now.hour == 14 and now.minute == 0 and now.second < 10:
                        send_monthly_message(loss_percentage)
                        
                except ValueError:
                    print(f"Invalid price for {coin_name}")
            
        except json.JSONDecodeError:
            print("Error parsing statistics JSON")
    else:
        print("Statistics data not found.")

    try:
        initial_price = 0.3
        current_price = coinmarketcap
        loss_percentage = calculate_loss_percentage(initial_price, current_price)

        formatted_bitcoin = format_price(float(bitcoin), "bitcoin")
        formatted_ethereum = format_price(float(ethereum), "ethereum")
        formatted_solana = format_price(float(solana), "solana")
        formatted_xrp = format_price(float(xrp), "xrp")
        formatted_cardano = format_price(float(cardano), "cardano")
        formatted_px = format_price(float(coinmarketcap), "px")
        formatted_ton = format_price(float(x), "ton")  

        message_text = f"""
$PX {formatted_px}$  |  -{loss_percentage:.2f}%

$TON {formatted_ton}$ 
"""

        sent = bot.send_message(chat_id=chat_id, text=str(message_text), parse_mode="Markdown")

    except NameError:
        print("One or more coin prices not found yet.")

    time.sleep(60)
