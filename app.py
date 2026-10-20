import asyncio
import logging
import os
from os.path import dirname, join

from dotenv import load_dotenv
from telegram import (InlineQueryResultArticle, InputTextMessageContent,
                      Update, InlineKeyboardMarkup, InlineKeyboardButton)
from telegram.ext import (Application, CallbackQueryHandler,
                          CommandHandler, ContextTypes,
                          InlineQueryHandler, MessageHandler, filters)

from torrent_file import TorrentFile
from tpb_adaptor import TpbAdaptor, build_magnet_link
from db_service import get_db_service
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
# MAX_RESULTS_PER_QUERY = 50 (Telegram limit)
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'your_bot')

# Database service
db_service = None


async def initialize_database():
    """Initialize the database service."""
    global db_service
    db_service = await get_db_service()


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
        search_term = ' '.join(context.args[1:]) if len(context.args) > 1 else ''
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 View Magnet", callback_data=f"magnet:{btih}"),
            InlineKeyboardButton("🔑 View BTIH", callback_data=f"btih:{btih}"),
            InlineKeyboardButton("🔍 View Search", callback_data=f"search:{btih}:{search_term}"),
        ]])
        await update.message.reply_text(reply, reply_markup=keyboard)

        # Record in database
        user_id = update.effective_user.id
        if db_service:
            try:
                # Extract BTIH from magnet if needed
                from torrent_file import validate_input, extract_btih
                is_valid, input_type = validate_input(btih)
                actual_btih = btih
                if input_type == 'magnet':
                    actual_btih = extract_btih(btih)

                magnet_link = build_magnet_link(actual_btih)
                output_dir = os.environ.get('OUTPUT_DIR', './output')
                file_path = os.path.join(output_dir, output_path)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None

                await db_service.record_created_torrent(
                    user_id=user_id,
                    btih=actual_btih,
                    magnet_link=magnet_link,
                    search_term=search_term,
                    filename=output_path,
                    file_path=file_path,
                    file_size_bytes=file_size,
                )
                await db_service.record_event("torrent_created", user_id, {"btih": actual_btih})
            except Exception as e:
                logger.error(f"Failed to record torrent creation: {e}")
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
    """@bot inline search"""
    query = update.inline_query.query
    if not query:
        return

    user_id = update.inline_query.from_user.id
    logger.info(f'Inline: {query} from user {user_id}')

    loop = asyncio.get_running_loop()
    limit = int(os.environ.get('LIMIT', 30))
    all_results = await loop.run_in_executor(
        None,
        tpbAdaptor.fetch_magnet_links,
        query,
        limit
    )

    articles = []
    for magnet in all_results:
        btih = magnet['id']
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
        cache_time=300,
    )

    # Record search in database
    if db_service:
        try:
            await db_service.record_search(user_id, query, len(all_results))
            await db_service.record_event("inline_search", user_id, {"query": query, "results": len(all_results)})
        except Exception as e:
            logger.error(f"Failed to record search: {e}")


async def callback_view_magnet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'View Magnet' button callback"""
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
    logger.info(f'Callback view magnet: {btih}')

    magnet_link = build_magnet_link(btih)

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


async def callback_view_btih(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'View BTIH' button callback"""
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
    logger.info(f'Callback view btih: {btih}')

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


async def callback_view_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle 'View Search' button callback"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("search:"):
        if query.message:
            await query.message.reply_text("Invalid action")
        elif query.inline_message_id:
            await context.bot.edit_message_text(
                inline_message_id=query.inline_message_id,
                text="Invalid action"
            )
        return

    # Format: search:<btih>:<search_term>
    parts = data.split(":", 2)
    if len(parts) < 3:
        if query.message:
            await query.message.reply_text("Invalid search data")
        elif query.inline_message_id:
            await context.bot.edit_message_text(
                inline_message_id=query.inline_message_id,
                text="Invalid search data"
            )
        return

    search_term = parts[2].replace('_', ' ')
    logger.info(f'Callback view search: {search_term}')

    # Build the inline query command
    inline_command = f"@{BOT_USERNAME} {search_term}"

    text = f"🔍 Search command (tap to copy):\n\n`{inline_command}`"

    if query.message:
        await query.message.reply_text(text, parse_mode='Markdown')
    elif query.inline_message_id:
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
    callback_view_magnet, pattern=r'^magnet:'))
application.add_handler(CallbackQueryHandler(
    callback_view_btih, pattern=r'^btih:'))
application.add_handler(CallbackQueryHandler(
    callback_view_search, pattern=r'^search:'))


# Initialize database on startup
async def post_init(application: Application):
    """Initialize database after application starts."""
    await initialize_database()


application.post_init = post_init

# Start bot
print("Bot up and listening!")
application.run_polling()
