import os
import requests
import re
import json
import time
import telebot
from datetime import datetime
from dotenv import load_dotenv  # For local .env loading

# Load environment variables
load_dotenv()  # Only for local development (remove in production if not needed)

# Initialize the bot with env vars
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
    return f"-{abs(percentage):.2f}%" if current_price < initial_price else f"+{percentage:.2f}%"

def format_price(price, coin_name):
    if coin_name == "px":
        return round(price, 4)
    elif coin_name == "ton":
        return round(price, 2)
    return round(price)

# Rest of the code remains the same...
