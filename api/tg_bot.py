from dotenv import load_dotenv
import os
import telebot
from api import create_conversation
import json

load_dotenv()
telegram_token = os.getenv('TELEGRAM_TOKEN')

bot = telebot.TeleBot(telegram_token)

# Store user API keys temporarily (in production, use a database)
user_api_keys = {}

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    bot.reply_to(message, '''Welcome to OpenHands Bot! 🤖

Please send me your OpenHands API key to get started.

You can get your API key from: https://app.all-hands.dev/settings/api-keys''')

@bot.message_handler(func=lambda message: message.from_user.id not in user_api_keys and not message.text.startswith('/'))
def get_api_key(message):
    user_id = message.from_user.id
    api_key = message.text.strip()

    # Basic validation - check if it looks like an API key
    if len(api_key) > 10 and not ' ' in api_key:
        user_api_keys[user_id] = api_key
        bot.reply_to(message, "✅ API key stored successfully!\n\nNow you can send me any task and I'll create an OpenHands conversation for you.")
    else:
        bot.reply_to(message, "❌ That doesn't look like a valid API key. Please try again.\n\nAPI keys are usually long strings without spaces.")

@bot.message_handler(func=lambda message: message.from_user.id in user_api_keys and not message.text.startswith('/'))
def handle_task(message):
    user_id = message.from_user.id
    task = message.text

    try:
        # Pass the user's API key as a parameter (thread-safe approach)
        api_key = user_api_keys[user_id]
        result = create_conversation(task, api_key)
        bot.reply_to(message, f"🚀 Task initiated!\n\n{result}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error creating conversation: {str(e)}\n\nPlease check your API key and try again.")

@bot.message_handler(commands=['reset'])
def reset_command(message):
    user_id = message.from_user.id
    if user_id in user_api_keys:
        del user_api_keys[user_id]
    bot.reply_to(message, "🔄 API key reset. Please send your API key again to continue.")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
🤖 OpenHands Bot Commands:

/start - Start the bot and set up your API key
/reset - Reset your stored API key
/help - Show this help message

How to use:
1. Send /start to begin
2. Provide your OpenHands API key
3. Send any task and I'll create an OpenHands conversation for you!

Get your API key from: https://app.all-hands.dev/
    """
    bot.reply_to(message, help_text)

if __name__ == '__main__':
    print("🤖 OpenHands Telegram Bot started...")
    bot.polling(none_stop=True)
