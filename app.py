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
        reply = f'File created successfully, {output_path}'
    await update.message.reply_text(reply)


async def helper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help returns the general usage of the bot"""
    await update.message.reply_text(
        '''Hi there!
@living_room_bot search_phrase - inline search,
/start - brih|magnet [<name>],
/help - to view this message.''')


async def inline_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """@bot inline search with pagination"""
    query = update.inline_query.query
    if not query:
        return

    logger.info(f'Inline: {query}')

    loop = asyncio.get_running_loop()
    # Fetch more results than PAGE_SIZE to support pagination
    # We fetch LIMIT from env (default 30) or a larger amount for pagination
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
        # Create inline keyboard with action buttons
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "📥 Create .torrent",
                callback_data=f"create:{btih}"
            ),
            InlineKeyboardButton(
                "📋 Copy Magnet",
                url=magnet.get('magnet_link', '')
            ),
        ]])

        articles.append(
            InlineQueryResultArticle(
                id=btih,
                title=magnet['title'][:64],  # Telegram limit
                input_message_content=InputTextMessageContent(
                    magnet['command_msg']),
                description=magnet['description'][:256],  # Telegram limit
                reply_markup=keyboard,
            )
        )

    await update.inline_query.answer(
        articles,
        auto_pagination=True,  # PTB handles next_offset automatically
        cache_time=300,
    )


async def callback_create_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'Create .torrent' button callback"""
    query = update.callback_query
    await query.answer()

    # callback_data format: "create:<btih>"
    data = query.data
    if not data.startswith("create:"):
        await query.edit_message_text("Invalid action")
        return

    btih = data.split(":", 1)[1]
    logger.info(f'Callback create torrent: {btih}')

    # Create torrent file
    output_path = TorrentFile([btih, 'FromInline'], logger).create()
    if output_path is None:
        reply = 'Failed to create torrent file. Invalid BTIH.'
    elif output_path == '':
        reply = 'Failed to create file.'
    else:
        reply = f'✅ Torrent file created: {output_path}'

    await query.edit_message_text(reply)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the message back to the user"""
    if ("myip" in update.message.text):
        myport = os.environ.get('MYPORT')
        http = urllib3.PoolManager()
        myip = http.request('GET', 'https://ident.me').data.decode()
        output_msg = f'{myip}:{myport}'
        logger.info(f'myip: {update.message.chat.username}, {output_msg}')
        await update.message.reply_text(output_msg)
    else:
        logger.info(f'Echo: {update.message.chat.username}, {update.message.text}')
        await update.message.reply_text(f'Echo: {update.message.text}')


# Register handlers
application.add_handler(InlineQueryHandler(inline_lookup))
application.add_handler(CommandHandler('start', start, filters=approved_user_filter))
application.add_handler(CommandHandler('help', helper))
application.add_handler(MessageHandler(
    approved_user_filter & filters.TEXT & ~filters.COMMAND, echo))
application.add_handler(CallbackQueryHandler(
    callback_create_torrent, pattern=r'^create:'))


# Start bot
print("Bot up and listening!")
application.run_polling()
