import logging
from os.path import dirname, join, os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (CallbackContext, CommandHandler, MessageHandler,
                          Updater, Filters)

# __MAIN__
# Load .env params:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Setup Token:
TOKEN = os.environ.get('TELEGRAM_TOKEN')
approved_user_ids = os.environ.get('APPROVED_IDS').split(',')
updater = Updater(TOKEN, use_context=True)

# Logger setup:
logging_level = os.environ.get('LOG_LEVEL')
logging.basicConfig(level=logging_level)  # Affects the library
logger = logging.getLogger("TelegramBot")
logger_file_path = os.environ.get('LOG_PATH')
handler = logging.FileHandler(logger_file_path)
handler.setLevel('DEBUG')

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# '%(asctime)s [%(levelname)s] %(message)s')  # Remove
handler.setFormatter(formatter)
logger.addHandler(handler)

# Setup commands


def search(update: Update, context: CallbackContext) -> None:
    print('Got command')
    update.message.reply_text(f'Lookup {update.effective_user.first_name}')


updater.dispatcher.add_handler(CommandHandler('search', search))


def echo(update: Update, context: CallbackContext):
    print("We got a msg")
    update.message.reply_text(f'Echo: {update.message.text}')
    context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text)


# approved_user_filter = Filters.user(user_id=approved_user_ids)
echo_handler = MessageHandler(
    Filters.text & (~Filters.command), echo)
# approved_user_filter &
updater.dispatcher.add_handler(echo_handler)

print("Bot up and listening!")
updater.start_polling()
updater.idle()
