from os.path import dirname, join, os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, Updater


def hello(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f'Hello {update.effective_user.first_name}')


# __MAIN__
# Load .env params:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Setup Bot:
TOKEN = os.environ.get('TELEGRAM_TOKEN')
approved_ids = os.environ.get('APPROVED_IDS').split(',')

updater = Updater(TOKEN)

updater.dispatcher.add_handler(CommandHandler('hello', hello))

updater.start_polling()
updater.idle()
