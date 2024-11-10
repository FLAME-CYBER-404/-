import telebot
import requests
import json
import os
import time
import base64
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from threading import Thread
from flask import Flask

BOT_TOKEN = '6952221734:AAFKWViRgT-N9ve2Fhrpqmqo19iXBQ8gY_M'  # Token for the Telegram Bot
ADMIN_CHAT_ID = '6078665585'  # Admin's Telegram Chat ID
USERS_FILE = 'users.json'  # File to store the list of users
HUGGING_FACE_API_KEY = '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'  # Replace with your Hugging Face API key

bot = telebot.TeleBot(BOT_TOKEN)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            try:
                users = json.load(f)
                if isinstance(users, dict):
                    return users
                else:
                    print("Users file is not in the correct format, initializing a new one.")
            except json.JSONDecodeError:
                print("Error decoding JSON, initializing a new file.")
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

users = load_users()

def setup_commands():
    commands = [
        BotCommand("start", "Start interacting with the bot"),
        BotCommand("help", "List available commands"),
        BotCommand("upgrade", "Request to upgrade to premium subscription"),
        BotCommand("status", "Check your subscription status"),
    ]
    bot.set_my_commands(commands)

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('Send Notice', callback_data='send_notice'),
        InlineKeyboardButton('Show Ads', callback_data='show_ads'),
        InlineKeyboardButton('Total Users', callback_data='total_users'),
        InlineKeyboardButton('Add Premium User', callback_data='add_premium'),
        InlineKeyboardButton('Remove Premium User', callback_data='remove_premium'),
        InlineKeyboardButton('List Premium Users', callback_data='list_premium_users')
    )
    return keyboard

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.chat.id)
    if user_id not in users:
        users[user_id] = {
            'subscription': 'free',  
            'images_generated': 0,   
            'last_generated_time': 0  
        }
        save_users(users)
    welcome_text = (
        "🌟 Welcome to the Intelligence_fx Bot! 🌟\n\n"
        "This bot allows you to generate stunning images from your prompts. Here’s what you can do:\n"
        "🎨 Generate images with free quality (up to 10 images per day).\n"
        "🚀 Upgrade to premium for unlimited access and high-quality images.\n"
        "🖼️ Simply type your prompt and watch the magic happen!\n\n"
        "Use /help to see all available commands, and let your creativity flow!\n"
        "If you need assistance, feel free to reach out!"
    )
    
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['upgrade'])
def handle_upgrade(message):
    user_id = str(message.chat.id)
    
    # Check if the user is already premium
    if user_id in users and users[user_id]['subscription'] == 'premium':
        bot.reply_to(message, "You are already a premium user.")
        return
    
    # Notify your personal account with the user's chat ID and request
    bot.send_message(ADMIN_CHAT_ID, f"User {user_id} wants to buy premium access.")
    bot.reply_to(message, "Your request for premium access has been sent to the admin. Please wait for a response.")

@bot.message_handler(commands=['status'])
def handle_status(message):
    user_id = str(message.chat.id)
    if user_id in users:
        subscription_status = users[user_id]['subscription']
        bot.reply_to(message, f"Your subscription status: {subscription_status.capitalize()}")
    else:
        bot.reply_to(message, "You are not registered. Please start with /start.")

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "Available commands:\n"
        "/start - Start interacting with the bot.\n"
        "/help - List available commands.\n"
        "/upgrade - Request to upgrade to premium subscription.\n"
        "/status - Check your subscription status.\n\n"
        "How to use the bot:\n"
        "1. After starting the bot, simply type your prompt to generate an image.\n"
        "2. Free users can generate up to 10 images per day.\n"
        "3. If you reach your limit, wait 24 hours to generate more.\n"
        "4. Upgrade to premium for unlimited access to image generation.\n\n"
        "For support, contact the admin."
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if str(message.chat.id) == ADMIN_CHAT_ID:
        welcome_text = (
            "Welcome Admin! Here are your commands:\n"
            "/send_notice - Send a notice to all users.\n"
            "/show_ads - Show ads to all users.\n"
            "/total_users - Check total users.\n"
            "/add_premium - Add a premium user.\n"
            "/remove_premium - Remove premium user.\n"
            "/list_premium_users - List all premium users."
        )
        bot.reply_to(message, welcome_text, reply_markup=get_admin_keyboard())
    else:
        bot.reply_to(message, "You are not authorized to access admin commands.")

@bot.callback_query_handler(func=lambda call: True)
def handle_admin_callbacks(call):
    if str(call.message.chat.id) == ADMIN_CHAT_ID:
        if call.data == 'send_notice':
            bot.send_message(ADMIN_CHAT_ID, "Please enter the notice message:")
            bot.register_next_step_handler(call.message, send_notice_to_users)
        elif call.data == 'show_ads':
            bot.send_message(ADMIN_CHAT_ID, "Please enter the ad message:")
            bot.register_next_step_handler(call.message, send_ads_to_users)
        elif call.data == 'total_users':
            bot.send_message(ADMIN_CHAT_ID, f"Total Users: {len(users)}")
        elif call.data == 'add_premium':
            bot.send_message(ADMIN_CHAT_ID, "Please enter the user ID to add premium access:")
            bot.register_next_step_handler(call.message, add_premium_user)
        elif call.data == 'remove_premium':
            bot.send_message(ADMIN_CHAT_ID, "Please enter the user ID to remove premium access:")
            bot.register_next_step_handler(call.message, remove_premium_user)
        elif call.data == 'list_premium_users':
            premium_users = [user_id for user_id, data in users.items() if data['subscription'] == 'premium']
            if premium_users:
                bot.send_message(ADMIN_CHAT_ID, f"Premium Users: {', '.join(premium_users)}")
            else:
                bot.send_message(ADMIN_CHAT_ID, "No premium users found.")

@bot.message_handler(func=lambda message: True)
def handle_user_messages(message):
    user_id = str(message.chat.id)
    prompt = message.text

    if user_id in users:
        # Check subscription status
        subscription_status = users[user_id]['subscription']
        
        # Determine the limit for free users
        if subscription_status == 'free':
            current_time = time.time()
            if users[user_id]['images_generated'] < 10:
                bot.reply_to(message, "Generating image, please wait...")
                generate_image(message, prompt, free=True)  # Use free generation method
                users[user_id]['images_generated'] += 1
                users[user_id]['last_generated_time'] = current_time
                save_users(users)
            else:
                time_since_last_generation = current_time - users[user_id]['last_generated_time']
                if time_since_last_generation >= 86400:  # Reset limit after 24 hours
                    bot.reply_to(message, "Generating image, please wait...")
                    generate_image(message, prompt, free=True)  # Use free generation method
                    users[user_id]['images_generated'] = 1  # Reset count after usage
                    users[user_id]['last_generated_time'] = current_time
                    save_users(users)
                else:
                    remaining_time = 86400 - time_since_last_generation
                    remaining_hours = remaining_time // 3600
                    remaining_minutes = (remaining_time % 3600) // 60
                    bot.reply_to(message, f"You've reached the limit of 10 images. Please wait {remaining_hours} hours and {remaining_minutes} minutes before generating more.")
                    # Send premium advertisement message
                    premium_message = (
                        "✨ Want to generate unlimited images? ✨\n"
                        "Upgrade to premium to remove limits and access high-quality options!\n"
                        "Contact @Nonewhs for premium subscription details."
                    )
                    bot.send_message(message.chat.id, premium_message)
        else:
            bot.reply_to(message, "Generating image, please wait...")
            generate_image(message, prompt, free=False)  # Premium users have no limit
    else:
        bot.reply_to(message, "You are not registered. Please start with /start.")

def generate_image(message, prompt, free=True):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.1',
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }

        data = {'prompt': prompt}
        response = requests.post('https://own-ai.onrender.com/api/v1/generateImage', headers=headers, json=data)
        response_json = response.json()

        if response.status_code == 200 and 'data' in response_json and 'photo' in response_json['data']:
            image_data = base64.b64decode(response_json['data']['photo'])
            bot.send_photo(message.chat.id, image_data)
            
            # Send appropriate message based on user's subscription
            user_id = str(message.chat.id)
            if user_id in users and users[user_id]['subscription'] == 'premium':
                bot.send_message(message.chat.id, "🎉 Thank you for being a premium user! Enjoy your high-quality image! 🎉")
            else:
                premium_message = (
                    "🚀 Upgrade to premium for unlimited access! 🚀\n"
                    "Unlock all features and enjoy high-quality image generation.\n"
                    "Contact @Nonewhs for details."
                )
                bot.send_message(message.chat.id, premium_message)
        else:
            bot.reply_to(message, "Failed to generate the image. Please try again later.")
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

def send_notice_to_users(message):
    notice_message = message.text
    for user_id in users:
        try:
            bot.send_message(user_id, notice_message)
        except Exception as e:
            print(f"Failed to send message to user {user_id}: {e}")
    bot.send_message(ADMIN_CHAT_ID, "Notice sent to all users.")

def send_ads_to_users(message):
    ad_message = message.text
    for user_id in users:
        try:
            bot.send_message(user_id, ad_message)
        except Exception as e:
            print(f"Failed to send ad to user {user_id}: {e}")
    bot.send_message(ADMIN_CHAT_ID, "Ads sent to all users.")

def add_premium_user(message):
    user_id = message.text
    if user_id in users:
        users[user_id]['subscription'] = 'premium'
        save_users(users)
        bot.send_message(ADMIN_CHAT_ID, f"User {user_id} added as a premium user.")
    else:
        bot.send_message(ADMIN_CHAT_ID, "User ID not found.")

def remove_premium_user(message):
    user_id = message.text
    if user_id in users:
        users[user_id]['subscription'] = 'free'
        save_users(users)
        bot.send_message(ADMIN_CHAT_ID, f"User {user_id} removed from premium access.")
    else:
        bot.send_message(ADMIN_CHAT_ID, "User ID not found.")

app = Flask(__name__)

if __name__ == "__main__":
    setup_commands()
    Thread(target=bot.polling, kwargs={"none_stop": True}).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
                
