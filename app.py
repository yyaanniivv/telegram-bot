import logging
from os.path import dirname, join, os
from search import Scraper, fibo  # Remove fibo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (CallbackContext, CommandHandler, Filters,
                          MessageHandler, Updater)

import random  # Remove with fibo

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
scraper = Scraper(logger)

# Setup commands


def search(update: Update, context: CallbackContext) -> None:
    # a = fibo(random.randint(11, 20))
    res = scraper.request_magnet_links(context.args)
    print("******", res)
    update.message.reply_text(f'Lookup {context.args}')


# TODO: Accept magnet, and click/selection of a result
def echo(update: Update, context: CallbackContext):
    update.message.reply_text(f'Echo: {update.message.text}')
    # context.bot.send_message(
    #     chat_id=update.effective_chat.id, text=update.message.text)


search_handler = CommandHandler('search', search, approved_user_filter)
echo_handler = MessageHandler(
    approved_user_filter &
    Filters.text & (~Filters.command), echo)

updater.dispatcher.add_handler(echo_handler)
updater.dispatcher.add_handler(search_handler)

# Start bot
print("Bot up and listening!")
updater.start_polling()
updater.idle()
