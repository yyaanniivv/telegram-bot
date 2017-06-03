import telepot
from telepot.loop import MessageLoop
from os.path import join, dirname, os
from dotenv import load_dotenv
import time
import logging
import re

from pprint import pprint

# Load .env params:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Logger setup:
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TelegramBot")
logger_file_path = os.environ.get('LOG_PATH')

handler = logging.FileHandler(logger_file_path)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Setup Bot:
bot = telepot.Bot(os.environ.get('TELEGRAM-TOKEN'))
approved_ids = os.environ.get('APPROVED_IDS').split(',')

def create_torrent(text, date):
    p = re.compile('magnet:\?xt=urn:btih:([^&/]+)')
    matches = p.match(text)
    if matches:
        print(matches.group(1)) # as file name meat-hash.torrent
        output_path = os.path.join(os.environ.get('OUTPUT_DIR'), 'meta-' + str(date) + '.torrent')
        # output_path = os.path.join(os.environ.get('OUTPUT_DIR'), 'meta-'+ matches.group(1) + '.torrent')
        f1 = open(output_path, 'w+')
        f1.write('d10:magnet-uri' + str(len(text)) + ':' + text + 'e')
        f1.close()
        logger.info('Created file: ' + output_path)
    else:
        logger.info('No magnet matched. :-(')

def handle(msg):
    sender_id = msg['from']['id']
    # logger.info('sender_id: ' + str(sender_id))
    logger.info("Incoming message:")
    logger.info(msg)

    if str(sender_id) in approved_ids:
        # logger.info('Known user sent a message.')

        command = msg['text']
        # logger.info('Command is ' + command)

        if 'magnet' in command: #send msg ok
            bot.sendMessage(sender_id, msg['text'])
            create_torrent(msg['text'], msg['date'])
        elif command == 'help':
            bot.sendMessage(sender_id,"Hello! Send a magnet link you want to save.")
        else:
            bot.sendMessage(sender_id, "I don't know this command, try to use `help` command")
    else:
        #No reply to user, (401) Unauthorized
        logger.warn('Unknown user sent message')

logger.info('...Starting Torbot...')
MessageLoop(bot, handle).run_as_thread()

while 1:
    time.sleep(15)
