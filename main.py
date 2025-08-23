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
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

VIDEO, DESCRIPTION, SPONSOR_NAME, SPONSOR_LINK = range(4)

TG_DIRECTORIES_CHANNEL_ID = "-1001367214367"

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
        "Welcome! Please upload the video for your post.",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return VIDEO


async def get_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message and update.message.text in ("Exit", "Restart"):
        if update.message.text == "Exit":
            return await cancel(update, context)
        return await start_post(update, context)

    video_file_id = None
    if update.message and update.message.video:
        video_file_id = update.message.video.file_id
    elif (
        update.message
        and update.message.document
        and getattr(update.message.document, "mime_type", "")
    ):
        if update.message.document.mime_type.startswith("video"):
            video_file_id = update.message.document.file_id

    if video_file_id:
        context.user_data["video"] = video_file_id
        await update.message.reply_text(
            "Video received. Now enter the description for your post.",
            reply_markup=PERSISTENT_KEYBOARD,
        )
        return DESCRIPTION

    await update.message.reply_text(
        "Please upload a video file (any duration/dimensions).",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return VIDEO


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["description"] = text
    await update.message.reply_text(
        "Enter the Sponsor button text (this will be the label shown).",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return SPONSOR_NAME


async def get_sponsor_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["sponsor_name"] = text
    await update.message.reply_text(
        "Enter the Sponsor link (full URL).",
        reply_markup=PERSISTENT_KEYBOARD,
    )
    return SPONSOR_LINK


async def get_sponsor_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Exit":
        return await cancel(update, context)
    if text == "Restart":
        return await start_post(update, context)
    context.user_data["sponsor_link"] = text

    user_button = InlineKeyboardButton(
        context.user_data.get("sponsor_name", "Sponsor"),
        url=context.user_data["sponsor_link"],
    )
    fixed_button = InlineKeyboardButton(
        "Contact us for Sponsor - T.me/GoSmartMaster", url="https://t.me/GoSmartMaster"
    )
    markup = InlineKeyboardMarkup([[user_button], [fixed_button]])

    caption = context.user_data.get("description", "")

    await context.bot.send_video(
        chat_id=TG_DIRECTORIES_CHANNEL_ID,
        video=context.user_data.get("video"),
        caption=caption,
        reply_markup=markup,
    )

    await update.message.reply_text(
        f"Your post has been sent to T.me/TGDirectories.",
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
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(Exit|Restart)$"),
                start_post,
            ),
        ],
        states={
            VIDEO: [MessageHandler(filters.ALL, get_video)],
            DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)
            ],
            SPONSOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_sponsor_name)
            ],
            SPONSOR_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_sponsor_link)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
