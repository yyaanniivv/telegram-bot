import logging
from os.path import dirname, join, os

from dotenv import load_dotenv
from telegram import (InlineQueryResultArticle, InputTextMessageContent,
                      ParseMode, Update)
from telegram.ext import (CallbackContext, CommandHandler, Filters,
                          InlineQueryHandler, MessageHandler, Updater)

from torrent_file import TorrentFile
from tpb_adaptor import TpbAdaptor
import urllib3

# __MAIN__
# Load .env params:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Setup Token:
TOKEN = os.environ.get('TELEGRAM_TOKEN')
updater = Updater(TOKEN, use_context=True)
approved_user_ids = list(map(int, os.environ.get('APPROVED_IDS').split(',')))
approved_user_filter = Filters.user(user_id=approved_user_ids)

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


def start(update: Update, context: CallbackContext) -> None:
    """/start create torrent file from btih or magnet link"""
    if len(context.args) == 1:
        context.args.append('NoSearch')
    output_path = TorrentFile(context.args, logger).create()
    reply = 'Failed to create file' if output_path == '' else f'File created successfully, {output_path}'
    update.message.reply_text(reply)


def helper(update: Update, context: CallbackContext) -> None:
    """/help returns the general usage of the bot"""
    update.message.reply_text(
        '''Hi there!
@living_room_bot search_phrase - inline search,
/start - brih|magnet [<name>],
/help - to view this message.''')


def inline_lookup(update: Update, context: CallbackContext) -> None:
    """@bot inline search """
    logger.info(f'Inline: {update.inline_query.query}')
    results = tpbAdaptor.fetch_magnet_links(
        update.inline_query.query, int(os.environ.get('LIMIT')))
    articles = list()
    for magnet in results:
        articles.append(
            InlineQueryResultArticle(
                id=magnet['id'],
                title=magnet['title'],
                input_message_content=InputTextMessageContent(
                    magnet['command_msg']),
                description=magnet['description'],
            )
        )
    context.bot.answer_inline_query(update.inline_query.id, articles)


def echo(update: Update, context: CallbackContext):
    """Echo the message back to the user"""
    if("myip" in update.message.text):
        myport = os.environ.get('MYPORT')
        http = urllib3.PoolManager()
        myip = http.request('GET', 'https://ident.me').data.decode()
        output_msg = f'{myip}:{myport}'
        logger.info(f'myip: {update.message.chat.username}, {output_msg}')
        update.message.reply_text(output_msg)
    else:
        logger.info(f'Echo: {update.message.chat.username}, {update.message.text}')
        update.message.reply_text(f'Echo: {update.message.text}')


inline_handler = InlineQueryHandler(inline_lookup)
start_handler = CommandHandler('start', start, approved_user_filter)
help_handler = CommandHandler('help', helper)
echo_handler = MessageHandler(
    approved_user_filter &
    Filters.text & (~Filters.command), echo)

updater.dispatcher.add_handler(echo_handler)
updater.dispatcher.add_handler(start_handler)
updater.dispatcher.add_handler(help_handler)
updater.dispatcher.add_handler(inline_handler)


# Start bot
print("Bot up and listening!")
updater.start_polling()
updater.idle()
