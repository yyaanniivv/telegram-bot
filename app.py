import logging
from os.path import dirname, join, os

from dotenv import load_dotenv
from telegram import (InlineQueryResultArticle, InputTextMessageContent,
                      ParseMode, Update)
from telegram.ext import (CallbackContext, CommandHandler, Filters,
                          InlineQueryHandler, MessageHandler, Updater)

from tpb_adaptor import TpbAdaptor

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
handler.setLevel('DEBUG')

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
tpbAdaptor = TpbAdaptor(logger)

# Setup commands


def start(update: Update, context: CallbackContext) -> None:
    return


def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        '''Hi there!
@living_room_bot <search phrase> - inline,
/start <magnet>,
/help to view this message.
        ''',)


def inline_lookup(update: Update, context: CallbackContext) -> None:
    # TODO: test approved_user_filter(update.message) to filter out other users.
    results = tpbAdaptor.request_magnet_links(
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
    update.message.reply_text(f'Echo: {update.message.text}')
    # context.bot.send_message(
    #     chat_id=update.effective_chat.id, text=update.message.text)


inline_handler = InlineQueryHandler(inline_lookup)
# start_handler = CommandHandler('start', start, approved_user_filter)
help_handler = CommandHandler('help', help)
echo_handler = MessageHandler(
    approved_user_filter &
    Filters.text & (~Filters.command), echo)

updater.dispatcher.add_handler(echo_handler)
# updater.dispatcher.add_handler(start_handler)
updater.dispatcher.add_handler(help_handler)
updater.dispatcher.add_handler(inline_handler)


# Start bot
print("Bot up and listening!")
updater.start_polling()
updater.idle()
