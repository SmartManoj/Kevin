from dotenv import load_dotenv
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from api import create_conversation
import json

load_dotenv()
slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
slack_app_token = os.getenv('SLACK_APP_TOKEN')

app = App(token=slack_bot_token)

# Store user API keys temporarily (in production, use a database)
user_api_keys = {}

@app.command("/start")
def start_command(ack, respond, command):
    ack()
    user_id = command['user_id']

    if user_id not in user_api_keys:
        respond(
            "🤖 Welcome to OpenHands Bot!\n\n"
            "To get started, please send me your OpenHands API key.\n"
            "You can get your API key from: https://app.all-hands.dev/\n\n"
            "Just type your API key in a message (not as a command)."
        )
    else:
        respond(
            "✅ You're already set up!\n\n"
            "Send me any task and I'll create an OpenHands conversation for you.\n"
            "Use `/reset` to change your API key or `/help` for more commands."
        )

@app.message()
def handle_message(message, say):
    user_id = message['user']
    text = message.get('text', '').strip()

    # Skip if it's a command (starts with /)
    if text.startswith('/'):
        return

    # If user hasn't provided API key yet
    if user_id not in user_api_keys:
        # Basic validation - check if it looks like an API key
        if len(text) > 10 and ' ' not in text:
            user_api_keys[user_id] = text
            say("✅ API key stored successfully!\n\nNow you can send me any task and I'll create an OpenHands conversation for you.")
        else:
            say("❌ That doesn't look like a valid API key. Please try again.\n\nAPI keys are usually long strings without spaces.")
        return

    # Handle task if user has API key
    try:
        # Pass the user's API key as a parameter (thread-safe approach)
        api_key = user_api_keys[user_id]
        result = create_conversation(text, api_key)
        say(f"🚀 Task initiated!\n\n{result}")

    except Exception as e:
        say(f"❌ Error creating conversation: {str(e)}\n\nPlease check your API key and try again.")

@app.command("/reset")
def reset_command(ack, respond, command):
    ack()
    user_id = command['user_id']

    if user_id in user_api_keys:
        del user_api_keys[user_id]

    respond("🔄 API key reset. Please send your API key again to continue.")

@app.command("/help")
def help_command(ack, respond, command):
    ack()
    help_text = """
🤖 OpenHands Bot Commands:

`/start` - Start the bot and set up your API key
`/reset` - Reset your stored API key
`/help` - Show this help message

How to use:
1. Send `/start` to begin
2. Provide your OpenHands API key (just type it in a message)
3. Send any task and I'll create an OpenHands conversation for you!

Get your API key from: https://app.all-hands.dev/
    """
    respond(help_text)

@app.event("app_mention")
def handle_app_mention(event, say):
    user_id = event['user']
    text = event.get('text', '').strip()

    # Remove the bot mention from the text
    text = ' '.join(text.split()[1:])  # Remove first word (the mention)

    if not text:
        say("👋 Hi! Send me a task and I'll create an OpenHands conversation for you!\n\nUse `/help` for more information.")
        return

    # If user hasn't provided API key yet
    if user_id not in user_api_keys:
        say("🔑 Please provide your OpenHands API key first.\n\nUse `/start` to get started or just send me your API key.")
        return

    # Handle task if user has API key
    try:
        # Pass the user's API key as a parameter (thread-safe approach)
        api_key = user_api_keys[user_id]
        result = create_conversation(text, api_key)
        say(f"🚀 Task initiated!\n\n{result}")

    except Exception as e:
        say(f"❌ Error creating conversation: {str(e)}\n\nPlease check your API key and try again.")

if __name__ == '__main__':
    print("🤖 OpenHands Slack Bot started...")
    handler = SocketModeHandler(app, slack_app_token)
    handler.start()
