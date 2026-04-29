import os
import re
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Keep-Alive Web Server ─────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is alive!", 200

def keep_alive():
    thread = threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080), daemon=True)
    thread.start()

# ── URL Detection ─────────────────────────────────────────
URL_PATTERN = re.compile(
    r"(https?://[^\s]+)"
    r"|(www\.[^\s]+\.[^\s]+)"
    r"|([^\s]+\.(com|net|org|io|xyz|info|me|ly|gg|tv|co|app|dev|link|site|"
    r"online|store|shop|click|page|live|news|pro|tech|ai|club|fun|top|win|"
    r"vip|best|now|today|world|space|wiki|one|plus|media|digital|social|blog|"
    r"zone|city|life|team|works|tools|edu|university|college)\b)",
    re.IGNORECASE,
)

LINK_ENTITY_TYPES = {"url", "text_link"}

# Admin ও Owner যে status-গুলো হলে exempt হবে
EXEMPT_STATUSES = {"administrator", "creator"}


def message_has_link(update: Update) -> bool:
    message = update.effective_message
    if not message:
        return False

    entities = list(message.entities or []) + list(message.caption_entities or [])
    for entity in entities:
        if entity.type in LINK_ENTITY_TYPES:
            return True

    text = message.text or message.caption or ""
    if URL_PATTERN.search(text):
        return True

    return False


async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return False

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in EXEMPT_STATUSES
    except Exception as e:
        logger.warning(f"Could not check admin status: {e}")
        return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    chat_type = update.effective_chat.type
    if chat_type not in ("group", "supergroup"):
        return

    if not message_has_link(update):
        return

    # Admin বা Owner হলে কিছুই করবে না
    if await is_admin_or_owner(update, context):
        logger.info(f"Skipped (admin/owner) | User: {update.effective_user.id}")
        return

    try:
        await message.delete()
        logger.info(f"Deleted | Chat: {update.effective_chat.id} | User: {update.effective_user.id}")
    except Exception as e:
        logger.warning(f"Could not delete: {e}")


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    keep_alive()

    telegram_app = ApplicationBuilder().token(token).build()
    telegram_app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot is running...")
    telegram_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
