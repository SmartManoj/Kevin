import os
import sys

import telebot
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
BOT_TOKEN = os.environ['BOT_TOKEN']
USER_ID = os.environ['USER_ID']

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

file_path = sys.argv[1]
# Send the file
with open(file_path, 'rb') as file:
    bot.send_document(USER_ID, file)

print('File sent successfully!')
