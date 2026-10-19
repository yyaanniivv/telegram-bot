import asyncio
import logging
from os.path import dirname, join, os

from dotenv import load_dotenv
from telegram import (InlineQueryResultArticle, InputTextMessageContent,
                      Update, InlineKeyboardMarkup, InlineKeyboardButton)
from telegram.ext import (Application, CallbackQueryHandler,
                          CommandHandler, ContextTypes,
                          InlineQueryHandler, MessageHandler, filters)

from torrent_file import TorrentFile
from tpb_adaptor import TpbAdaptor
import urllib3

# __MAIN__
# Load .env params:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Validate critical env vars:
SEARCH_URL = os.environ.get('SEARCH_URL', '')
if not SEARCH_URL.startswith('https://'):
    raise ValueError(f'SEARCH_URL must use HTTPS (got: {SEARCH_URL})')

# Setup Token:
TOKEN = os.environ.get('TELEGRAM_TOKEN')
application = Application.builder().token(TOKEN).build()
approved_user_ids = list(map(int, os.environ.get('APPROVED_IDS').split(',')))
approved_user_filter = filters.User(user_id=approved_user_ids)

# Logger setup:
logging_level = os.environ.get('LOG_LEVEL')
logging.basicConfig(level=logging_level)  # Affects the bot library
logger = logging.getLogger("TelegramBot")
logger_file_path = os.environ.get('LOG_PATH')
handler = logging.FileHandler(logger_file_path)
handler.setLevel(logging_level)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
tpbAdaptor = TpbAdaptor(logger)

# Constants
PAGE_SIZE = 20


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start create torrent file from btih or magnet link"""
    if len(context.args) == 1:
        context.args.append('NoSearch')
    output_path = TorrentFile(context.args, logger).create()
    if output_path is None:
        reply = 'Invalid input. Please provide a valid BTIH (40 hex chars) or magnet link.'
    elif output_path == '':
        reply = 'Failed to create file'
    else:
        reply = f'✅ Torrent file created: {output_path}\n\nTap a button below to view:'
        # Add view buttons to the reply
        btih = context.args[0]
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 View Magnet", callback_data=f"magnet:{btih}"),
            InlineKeyboardButton("🔑 View BTIH", callback_data=f"btih:{btih}"),
        ]])
        await update.message.reply_text(reply, reply_markup=keyboard)
        return
    await update.message.reply_text(reply)


async def helper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help returns the general usage of the bot"""
    await update.message.reply_text(
        '''Hi there!
@living_room_bot search_phrase - inline search,
/start - btih|magnet [<name>],
/help - to view this message.''')


async def inline_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """@bot inline search with pagination"""
    query = update.inline_query.query
    if not query:
        return

    logger.info(f'Inline: {query}')

    loop = asyncio.get_running_loop()
    # Fetch more results than PAGE_SIZE to support pagination
    fetch_limit = max(int(os.environ.get('LIMIT', 30)), PAGE_SIZE * 3)
    all_results = await loop.run_in_executor(
        None,
        tpbAdaptor.fetch_magnet_links,
        query,
        fetch_limit
    )

    # Parse offset for pagination
    offset = update.inline_query.offset
    start = int(offset) if offset and offset.isdigit() else 0
    end = start + PAGE_SIZE
    page_results = all_results[start:end]
    articles = []
    for magnet in page_results:
        btih = magnet['id']
        # No inline keyboard in results - buttons will be added by start handler
        articles.append(
            InlineQueryResultArticle(
                id=btih,
                title=magnet['title'][:64],
                input_message_content=InputTextMessageContent(
                    magnet['command_msg']),
                description=magnet['description'][:256],
            )
        )

    await update.inline_query.answer(
        articles,
        auto_pagination=True,
        cache_time=300,
    )


async def callback_copy_magnet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Copy Magnet' button callback"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("magnet:"):
        if query.message:
            await query.message.reply_text("Invalid action")
        elif query.inline_message_id:
            await context.bot.edit_message_text(
                inline_message_id=query.inline_message_id,
                text="Invalid action"
            )
        return

    btih = data.split(":", 1)[1]
    logger.info(f'Callback copy magnet: {btih}')

    magnet_prefix = os.environ.get('MAGNET_PREFIX', 'magnet:?xt=urn:btih:')
    magnet_suffix = os.environ.get('MAGNET_SUFFIX', '')
    magnet_link = f"{magnet_prefix}{btih}{magnet_suffix}"

    text = f"📋 Magnet link:\n\n`{magnet_link}`"

    if query.message:
        # Regular message - send new message
        await query.message.reply_text(text, parse_mode='Markdown')
    elif query.inline_message_id:
        # Inline message - edit the inline message
        await context.bot.edit_message_text(
            inline_message_id=query.inline_message_id,
            text=text,
            parse_mode='Markdown'
        )


async def callback_copy_btih(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Copy BTIH' button callback"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("btih:"):
        if query.message:
            await query.message.reply_text("Invalid action")
        elif query.inline_message_id:
            await context.bot.edit_message_text(
                inline_message_id=query.inline_message_id,
                text="Invalid action"
            )
        return

    btih = data.split(":", 1)[1]
    logger.info(f'Callback copy btih: {btih}')

    text = f"🔑 BTIH:\n\n`{btih}`"

    if query.message:
        # Regular message - send new message
        await query.message.reply_text(text, parse_mode='Markdown')
    elif query.inline_message_id:
        # Inline message - edit the inline message
        await context.bot.edit_message_text(
            inline_message_id=query.inline_message_id,
            text=text,
            parse_mode='Markdown'
        )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the message back to the user"""
    message = update.message or update.edited_message
    if not message or not message.text:
        return

    if ("myip" in message.text):
        myport = os.environ.get('MYPORT')
        http = urllib3.PoolManager()
        myip = http.request('GET', 'https://ident.me').data.decode()
        output_msg = f'{myip}:{myport}'
        logger.info(f'myip: {message.chat.username}, {output_msg}')
        await message.reply_text(output_msg)
    else:
        logger.info(f'Echo: {message.chat.username}, {message.text}')
        await message.reply_text(f'Echo: {message.text}')


# Register handlers
application.add_handler(InlineQueryHandler(inline_lookup))
application.add_handler(CommandHandler('start', start, filters=approved_user_filter))
application.add_handler(CommandHandler('help', helper))
application.add_handler(MessageHandler(
    approved_user_filter & filters.TEXT & ~filters.COMMAND, echo))
application.add_handler(CallbackQueryHandler(
    callback_copy_magnet, pattern=r'^magnet:'))
application.add_handler(CallbackQueryHandler(
    callback_copy_btih, pattern=r'^btih:'))


# Start bot
print("Bot up and listening!")
application.run_polling()
