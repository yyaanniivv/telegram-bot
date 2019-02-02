# Env variables
from os.path import join, dirname, os
from dotenv import load_dotenv

# Scraper
import urllib3
from bs4 import BeautifulSoup

# Telegram Bot
import asyncio
import telepot
from telepot.aio.loop import MessageLoop
from telepot.aio.helper import InlineUserHandler, AnswererMixin
from telepot.aio.delegate import per_chat_id, per_inline_from_id, create_open, pave_event_space

# Bot logic
import logging

# Output file logic
import re

from lib import Bot

# __MAIN__
# Load .env params:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Setup Bot:
TOKEN = os.environ.get('TELEGRAM_TOKEN')
approved_ids = os.environ.get('APPROVED_IDS').split(',')

# Logger setup:
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("TelegramBot")
logger_file_path = os.environ.get('LOG_PATH')

handler = logging.FileHandler(logger_file_path)

# Set logger to higher level for production
logging_level = os.environ.get('LOG_LEVEL')
if(logging_level == 'warning'):
    handler.setLevel(logging.WARNING)
elif(logging_level == 'debug'):
    handler.setLevel(logging.DEBUG)
elif(logging_level == 'info'):
    handler.setLevel(logging.INFO)


formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

Bot().start()
