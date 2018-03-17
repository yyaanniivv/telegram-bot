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


# TODO: Extract to two classes, scraper per SEARCH_URL and magnet_object

#  scraper maybe inhert a interface which will have: #get_articles
#  magnet_object will have to_string, to_article, to_json
def get_magnet_details(table):
    columns = table.find_all('td')
    description_object = {
        'uploaded': columns[1].text.strip(),
        'size': columns[2].text.strip(),
        'comments': columns[3].text.strip(),
        'seeders ^': columns[4].text.strip(),
        'leachers v': columns[5].text.strip(),
        'completed': columns[6].text.strip(),
    }
    magnet_object = {
        'title': columns[0].text.strip(),
        'magnet_link': columns[0].a.get('href'),  # this will be sent back to the bot.
        'description': ' | '.join('{}:{}'.format(key.capitalize(), val) for key, val in description_object.items()),
        # 'url': table.a.get('href'), # Is this needed?
    }
    return magnet_object


# Fix broken html
def format_html(html_byte):
    # decode byte to string
    html_str = html_byte.decode()

    # remove all redundant </form> tags. (all but the first one)
    a = html_str.replace("</form>", "</placeholdertag>", 1)
    b = a.replace("</form>", "")
    return b.replace("</placeholdertag>", "</form>", 1)


# Returns array of magnet objects
# returns [{magnet_object}, {magnet_object},]
def request_magnet_links(search_phrase, limit=10):
    # substitue space with '+'
    search_path = os.environ.get('SEARCH_URL') + search_phrase.replace(' ', '+')
    user_agent = {'User-Agent': os.environ.get('USER_AGENT')}
    magnet_objects = []

    http = urllib3.PoolManager(headers=user_agent)
    r1 = http.request('GET', search_path)

    if r1.status != 200:
        logger.debug(search_path)
        logger.debug(r1.status)
        logger.debug(r1.data)
    else:
        html_str = format_html(r1.data)
        soup = BeautifulSoup(html_str, 'html.parser')
        profile1_divs = soup.find_all('div', {'id': 'profile1'})

        for div in profile1_divs[1: 1 + limit]:
            table = div.find('table')
            magnet_objects += [get_magnet_details(table)]

    return magnet_objects


# TODO: end of classes


# Returns [{article},{article},]
def build_articles(search_phrase):
    articles = []
    for magnet in request_magnet_links(search_phrase):
        articles += [{
            'id': magnet['magnet_link'],  # Needs to be unique
            'type': 'article',
            'title': magnet['title'],
            'message_text': magnet['magnet_link'],
            'description': magnet['description']
        }]
    return articles


def create_magnet_articles(query_string):
    return build_articles(query_string)


# Articles:
# =========
# call function to return the results:
# 'message_text': char+'msg_text' << should be the btih magnet!!!!
# 'title': the title of the magnet
#  should have a subtitle with: uploaded | size | comments | seeders | leachers | completed
# article type https://core.telegram.org/bots/api#inline-mode

# depricated
# def create_a_z_articles(query_string):
#     a_z = string.ascii_lowercase
#     letters = a_z[a_z.index(query_string[0]):]
#     articles = []
#
#     for char in letters:
#         articles += [{'type': 'article',
#                          'id': char, 'title': char, 'message_text': char+'msg_text'}]
#     return articles


# Will lookup the list of magnets.
class InlineHandler(InlineUserHandler, AnswererMixin):
    def __init__(self, *args, **kwargs):
        super(InlineHandler, self).__init__(*args, **kwargs)

    def on_inline_query(self, msg):
        def compute_answer():
            query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
            # print(self.id, ':', 'Inline Query:', query_id, from_id, query_string)

            articles = create_magnet_articles(query_string)
            # articles = create_a_z_articles(query_string)
            # print(articles)

            return articles

        self.answerer.answer(msg, compute_answer)

    def on_chosen_inline_result(self, msg):
        from pprint import pprint
        pprint(msg)
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        print(self.id, ':', 'Chosen Inline Result:', result_id, from_id, query_string)


# Accepts magnet -> resuts infile in watch path.
class DirectMsgHandler(telepot.aio.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(DirectMsgHandler, self).__init__(*args, **kwargs)
        # self._count = 0 #original line

    async def on_chat_message(self, msg):
        # self._count += 1 #original line
        # await self.sender.sendMessage(self._count) #original line
        sender_id = msg['from']['id']
        logger.debug('sender_id: ' + str(sender_id))
        logger.info("Incoming message:")
        logger.info(msg)

        if str(sender_id) in approved_ids:
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


def create_torrent(text, date):
    pattern = re.compile('magnet:\?xt=urn:btih:([^&/]+)')
    matches = pattern.match(text)
    if matches:
        logger.info('matches.groups(1):' + matches.group(1))

        # TODO: Send name  for file
        output_path = os.path.join(os.environ.get('OUTPUT_DIR'), 'meta-' + str(date) + '.torrent')
        # output_path = os.path.join(os.environ.get('OUTPUT_DIR'), 'meta-'+ matches.group(1) + '.torrent')
        f1 = open(output_path, 'w+')
        f1.write('d10:magnet-uri' + str(len(text)) + ':' + text + 'e')
        f1.close()
        logger.info('Created file: ' + output_path)
    else:
        logger.info('No magnet matched. :-(')


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
handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

bot = telepot.aio.DelegatorBot(TOKEN, [
    pave_event_space()(
        per_inline_from_id(), create_open, InlineHandler, timeout=10),
    pave_event_space()(
        per_chat_id(), create_open, DirectMsgHandler, timeout=60),

])
loop = asyncio.get_event_loop()

loop.create_task(MessageLoop(bot).run_forever())
print('Listening ...')

loop.run_forever()
