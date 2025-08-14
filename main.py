import os
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

TITLE, DESCRIPTION, PHOTO, BUTTON_NAME, BUTTON_URL, TARGET_TYPE, TARGET_ID = range(7)

PERSISTENT_KEYBOARD = ReplyKeyboardMarkup(
    [["Restart", "Exit"]],
    resize_keyboard=True,
    one_time_keyboard=False,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_env_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment.")
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment.")
    return token


async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome! I can help you create and send a post.\n\nPlease send the post title.",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["title"] = text
    await update.message.reply_text(
        "Now send the description for your post.",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["description"] = text
    await update.message.reply_text(
        "Send a photo for the post or type skip to continue without an image.",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text in ("Exit", "Restart"):
        if update.message.text == "Exit":
            return await cancel(update, context)
        else:
            return await start_post(update, context)
    if update.message.photo:
        photo_file = update.message.photo[-1].file_id
        context.user_data["photo"] = photo_file
        logger.info("Photo received.")
        await update.message.reply_text(
            "Enter the button text for your post.",
            reply_markup=PERSISTENT_KEYBOARD,
        )
        return BUTTON_NAME
    await update.message.reply_text(
        "Please send a photo or type skip.",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return PHOTO


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text in ("Exit", "Restart"):
        if update.message.text == "Exit":
            return await cancel(update, context)
        else:
            return await start_post(update, context)
    context.user_data["photo"] = None
    await update.message.reply_text(
        "Enter the button text for your post.",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return BUTTON_NAME


async def get_button_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["button_name"] = text
    await update.message.reply_text(
        "Enter the button URL.",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return BUTTON_URL


async def get_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["button_url"] = text
    keyboard = [
        [InlineKeyboardButton("Telegram Directory", callback_data="directory")],
        [InlineKeyboardButton("This chat", callback_data="this_chat")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Where do you want to send the post?",
        reply_markup=reply_markup,
    )
    return TARGET_TYPE


async def get_target_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "directory":
        context.user_data["target_id"] = "-1001367214367"
        await query.edit_message_text("Sending to Telegram Directory...")
    elif query.data == "this_chat":
        context.user_data["target_id"] = str(query.message.chat.id)
        await query.edit_message_text("Sending to this chat...")
    else:
        await query.edit_message_text("Invalid option.")
        return ConversationHandler.END

    class DummyMessage:
        def __init__(self, text):
            self.text = text

    dummy_update = Update(
        update.update_id, message=DummyMessage(context.user_data["target_id"])
    )
    return await get_target_id(dummy_update, context)


async def get_target_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["target_id"] = text
    button = InlineKeyboardButton(
        context.user_data["button_name"], url=context.user_data["button_url"]
    )
    markup = InlineKeyboardMarkup([[button]])
    message_text = f"{context.user_data['title']}\n\n{context.user_data['description']}"
    target_id = context.user_data["target_id"]
    if context.user_data["photo"]:
        await context.bot.send_photo(
            chat_id=target_id,
            photo=context.user_data["photo"],
            caption=message_text,
            reply_markup=markup,
        )
    else:
        await context.bot.send_message(
            chat_id=target_id,
            text=message_text,
            reply_markup=markup,
        )
    await update.message.reply_text(
        f"Your post has been sent to {target_id}.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Post creation cancelled.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    token = get_env_token()
    application = Application.builder().token(token).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("create_post", start_post),
            CommandHandler("start", start_post),
            # Only trigger on text that is not "Exit" or "Restart"
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(Exit|Restart)$"),
                start_post,
            ),
        ],
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
            TARGET_TYPE: [CallbackQueryHandler(get_target_type)],
            TARGET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_target_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
