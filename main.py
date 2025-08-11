from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import logging

# Conversation state definitions
TITLE, DESCRIPTION, PHOTO, BUTTON_NAME, BUTTON_URL = range(5)

# Logger setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📌 Send me the post **title**.")
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📝 Now send me the **description**.")
    return DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "🖼️ Send me a **photo for the post** or type `skip` to continue without image."
    )
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        photo_file = update.message.photo[-1].file_id
        context.user_data["photo"] = photo_file
        logger.info("Photo received.")
        await update.message.reply_text("🔘 Enter the **button text**.")
        return BUTTON_NAME

    await update.message.reply_text("❌ Please send a photo or type `skip`.")
    return PHOTO


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["photo"] = None
    await update.message.reply_text("🔘 Enter the **button text**.")
    return BUTTON_NAME


async def get_button_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["button_name"] = update.message.text
    await update.message.reply_text("🔗 Enter the **button URL**.")
    return BUTTON_URL


async def get_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["button_url"] = update.message.text

    button = InlineKeyboardButton(
        context.user_data["button_name"], url=context.user_data["button_url"]
    )
    markup = InlineKeyboardMarkup([[button]])
    message_text = (
        f"**{context.user_data['title']}**\n\n{context.user_data['description']}"
    )

    if context.user_data["photo"]:
        await update.message.reply_photo(
            photo=context.user_data["photo"],
            caption=message_text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            message_text, reply_markup=markup, parse_mode="Markdown"
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Post creation cancelled.")
    return ConversationHandler.END


def main() -> None:
    application = (
        Application.builder()
        .token("8057030039:AAE195NboYMSyoGBchcEWiJDSX6UJ1Eo4V8")
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("create_post", start_post)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                MessageHandler(filters.Regex("^(skip|Skip)$"), skip_photo),
            ],
            BUTTON_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_button_name)
            ],
            BUTTON_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_button_url)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    logger.info("🚀 Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
