import requests
import pymongo
import re
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# Configuration
TOKEN = "7834485675:AAEF8h--NyCy7IAHWrRAZ2vYUGP69vz-9GE"
OWNER_ID = 7593550190  # Replace with your numeric Telegram ID
MONGODB_URI = "mongodb+srv://SiestaXMusic:BGMI272@cluster0.nik6j.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# MongoDB connection
client = pymongo.MongoClient(MONGODB_URI)
db = client["ai_chatbot_db"]
users_collection = db["users"]

# Ensure indexes for efficient queries
users_collection.create_index("user_id", unique=True)
users_collection.create_index("last_interaction")

def get_ai_response(query):
    """Fetch AI response from external API."""
    api_url = f"https://devil-web.in/api/ai.php?query={query}"
    try:
        response = requests.get(api_url)
        response.raise_for_status() 
        data = response.json()
        return data.get("response", "Sorry, I couldn't retrieve an answer.")
    except requests.exceptions.RequestException as e:
        return f"Error: Could not connect to the API. {e}"
    except ValueError:
        return "Error: Invalid response from the API."

def store_user(user_id, username, first_name):
    """Store user details in MongoDB."""
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "username": username,
            "first_name": first_name,
            "last_interaction": time.time()
        }},
        upsert=True
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    store_user(user.id, user.username, user.first_name)
    await update.message.reply_text("🤖 Hᴇʟʟᴏ! I'ᴍ DᴇᴇᴘSᴇᴇᴋ-R1, ᴀɴ ᴀʀᴛɪғɪᴄɪᴀʟ ɪɴᴛᴇʟʟɪɢᴇɴᴄᴇ ᴀssɪsᴛᴀɴᴛ Cʀᴇᴀᴛᴇᴅ Bʏ https://t.me/fn_network_back Pʟᴇᴀsᴇ Jᴏɪɴ Us.")

def escape_markdown_v2(text):
    """Escapes special characters for MarkdownV2 formatting in Telegram."""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(escape_chars) + r"])", r"\\\1", text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming user messages."""
    user = update.effective_user
    store_user(user.id, user.username, user.first_name)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    ai_response = get_ai_response(update.message.text)

    # Escape special characters before formatting
    escaped_response = escape_markdown_v2(ai_response)

    # Ensure it's properly formatted as a code block
    formatted_response = f"```\n{escaped_response}\n```"

    # Send the message, handling Telegram's length limitation
    try:
        await update.message.reply_text(formatted_response, parse_mode="MarkdownV2")
    except Exception:
        # If error occurs (e.g., long message), split and send in parts
        for chunk in [escaped_response[i:i+4000] for i in range(0, len(escaped_response), 4000)]:
            await update.message.reply_text(f"```\n{chunk}\
n```", parse_mode="MarkdownV2")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a broadcast message to all users (Admin only)."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a message to broadcast.")
        return

    message = " ".join(context.args)
    all_users = users_collection.find()
    success, failed = 0, 0

    for user in all_users:
        try:
            await context.bot.send_message(
                chat_id=user["user_id"],
                text=f"📢 Broadcast:\n\n{message}"
            )
            success += 1
        except Exception as e:
            print(f"Failed to send to {user['user_id']}: {e}")
            failed += 1
        time.sleep(0.1)

    await update.message.reply_text(
        f"📊 Broadcast completed!\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show total number of registered users (Admin only)."""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    total_users = users_collection.count_documents({})
    await update.message.reply_text(f"📊 Total users: {total_users}")

def main():
    """Start the bot."""
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
