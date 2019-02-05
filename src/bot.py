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

from .scraper import Scraper


# Will lookup the list of magnets.
class InlineHandler(InlineUserHandler, AnswererMixin):
    def __init__(self, *args, **kwargs):
        super(InlineHandler, self).__init__(*args, **kwargs)

    def on_inline_query(self, msg):
        def compute_answer():
            query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
            # print(self.id, ':', 'Inline Query:', query_id, from_id, query_string)
            articles = create_magnet_articles(query_string)
            return articles

        self.answerer.answer(msg, compute_answer)

    def on_chosen_inline_result(self, msg):
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        print(self.id, ':', 'Chosen Inline Result:', result_id, from_id, query_string)


# Accepts magnet -> results in file in OUTPUT_DIR path.
class DirectMsgHandler(telepot.aio.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(DirectMsgHandler, self).__init__(*args, **kwargs)

    async def on_chat_message(self, msg):
        sender_id = msg['from']['id']
        logger.debug('sender_id: ' + str(sender_id))
        logger.info("Incoming message:")
        logger.info(msg)

        if str(sender_id) in self.approved_ids:
            logger.debug('Known user sent a message.')

            command = msg['text']
            logger.debug('Command is ' + command)

            if 'magnet' in command:
                create_torrent(msg['text'], msg['date'])
                logger.info(str(sender_id) + ' ' + msg['text'])
                await self.sender.sendMessage('Got ' + msg['text'][0:40] + '...')

            elif command == 'help':
                logger.info(str(sender_id) + ' ' + "Hello! Send a magnet link you want to save.")
                await self.sender.sendMessage("Hello! Send a magnet link you want to save.")

            else:
                logger.info(str(sender_id) + ' ' + "I don't know this command, try to use `help` command")
                await self.sender.sendMessage("I don't know this command, try to use `help` command")
        else:
            # No reply to user, (401) Unauthorized
            logger.warn('Unknown user sent message')

class Bot:
    def __init__(self):
        # Setup Bot:
        self.TOKEN = os.environ.get('TELEGRAM_TOKEN')
        self.approved_ids = os.environ.get('APPROVED_IDS').split(',')
        print('start bot')

    # Returns [{article},{article},]
    def build_articles(search_phrase):
        articles = []
        for magnet in Scraper.request_magnet_links(search_phrase):
            articles += [{
                'id': extract_btih(magnet['magnet_link']),  # Needs to be unique
                'type': 'article',
                'title': magnet['title'],
                'message_text': magnet['magnet_link'],
                'description': magnet['description']
            }]
        return articles


    def extract_btih(text):
        pattern = re.compile('magnet:\?xt=urn:btih:([^&/]+)')
        matches = pattern.match(text)
        return matches.groups(1)[0]


    def create_magnet_articles(query_string):
        return build_articles(query_string)


    # Articles:
    # =========
    # call function to return the results:
    # 'message_text': char+'msg_text' << should be the btih magnet!!!!
    # 'title': the title of the magnet
    #  should have a subtitle with: uploaded | size | comments | seeders | leachers | completed
    # article type https://core.telegram.org/bots/api#inline-mode

    def create_torrent(text, date):
        torrent_file_hash = extract_btih(text)  # This isn't needed, just a sanity to verify input.
        if torrent_file_hash:
            output_path = os.path.join(os.environ.get('OUTPUT_DIR'), 'meta-' + str(date) + '.torrent')
            f1 = open(output_path, 'w+')
            f1.write('d10:magnet-uri' + str(len(text)) + ':' + text + 'e')
            f1.close()
            logger.info('Created file: ' + output_path)
            # return success msg
        else:
            logger.info('No magnet matched. :-(')

    def start(self):
        bot = telepot.aio.DelegatorBot(self.TOKEN, [
            pave_event_space()(
                per_inline_from_id(), create_open, InlineHandler, timeout=10),
            pave_event_space()(
                per_chat_id(), create_open, DirectMsgHandler, timeout=60),

        ])
        loop = asyncio.get_event_loop()

        loop.create_task(MessageLoop(bot).run_forever())
        print('Listening ...')

        loop.run_forever()
