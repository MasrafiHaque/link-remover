import os
import re
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)

# Logging শুধু debug-এর জন্য (production-এ বন্ধ করতে পারো)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# URL detect করার regex pattern
URL_PATTERN = re.compile(
    r"(https?://[^\s]+)"          # http:// বা https:// দিয়ে শুরু
    r"|(www\.[^\s]+\.[^\s]+)"     # www. দিয়ে শুরু
    r"|([^\s]+\.(com|net|org|io|xyz|info|me|ly|gg|tv|co|app|dev|link|site|online|store|shop|click|page|live|news|pro|tech|ai|club|fun|top|win|vip|best|now|today|world|space|wiki|one|plus|media|digital|agency|studio|design|host|cloud|social|blog|zone|city|life|team|works|tools|solutions|services|company|group|global|international|network|systems|platform|software|web|email|mail|support|help|care|health|fit|sport|music|video|photo|art|game|play|shop|buy|sell|market|trade|finance|money|bank|pay|crypto|nft|dao|defi|token|coin|exchange|invest|fund|capital|venture|startup|inc|ltd|llc|corp|foundation|institute|academy|school|edu|university|college|learning|course|class|training|coaching|consulting|agency|services|solutions|tech|digital|media|creative|design|studio|lab|works|hub|center|base|hq)\b)"  # noqa: E501
    , re.IGNORECASE
)

# Telegram entity দিয়েও লিংক ধরা (forwarded বা embed লিংক)
LINK_ENTITY_TYPES = {"url", "text_link"}


def message_has_link(update: Update) -> bool:
    """
    মেসেজে কোনো লিংক আছে কিনা চেক করে।
    দুটি পদ্ধতিতে চেক করা হয়:
    1. Telegram-এর নিজস্ব entity (url, text_link)
    2. Regex দিয়ে raw text-এ URL খোঁজা
    """
    message = update.effective_message
    if not message:
        return False

    # পদ্ধতি ১: Entity check
    entities = list(message.entities or []) + list(message.caption_entities or [])
    for entity in entities:
        if entity.type in LINK_ENTITY_TYPES:
            return True

    # পদ্ধতি ২: Regex check (text বা caption-এ)
    text = message.text or message.caption or ""
    if URL_PATTERN.search(text):
        return True

    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    প্রতিটি মেসেজ চেক করে — লিংক থাকলে silently delete করে।
    কোনো reply বা notification পাঠায় না।
    """
    message = update.effective_message
    if not message:
        return

    # শুধু group/supergroup-এ কাজ করবে
    chat_type = update.effective_chat.type
    if chat_type not in ("group", "supergroup"):
        return

    if message_has_link(update):
        try:
            await message.delete()
            logger.info(
                f"Deleted link message | Chat: {update.effective_chat.id} "
                f"| User: {update.effective_user.id if update.effective_user else 'unknown'}"
            )
        except Exception as e:
            logger.warning(f"Could not delete message: {e}")


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = ApplicationBuilder().token(token).build()

    # সব ধরনের মেসেজ handle করবে (text, caption সহ)
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            handle_message,
        )
    )

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
