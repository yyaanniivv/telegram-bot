import json
import time
from datetime import datetime
from os.path import dirname, join, os

import urllib3
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

#  scraper maybe inhert a interface which will have: #get_articles
#  TODO: magnet_object will have to_string, to_article, to_json


def build_magnet_link(btih: str) -> str:
    """Build magnet link from BTIH using environment variables."""
    magnet_prefix = os.environ.get('MAGNET_PREFIX', 'magnet:?xt=urn:btih:')
    magnet_suffix = os.environ.get('MAGNET_SUFFIX', '')
    return f"{magnet_prefix}{btih}{magnet_suffix}"


def get_magnet_details(entry: object, search_phrase: str):
    """Convert raw TPB API entry to magnet object with full metadata."""
    magnet_link = build_magnet_link(entry['info_hash'])

    # Keep raw size in bytes for exact storage
    size_bytes = int(entry["size"])
    # Human-readable size
    size_human = str(round(size_bytes / 1024**2, 2)) + ' MiB'

    # Parse upload date
    uploaded_date = datetime.fromtimestamp(int(entry['added'])).date()

    magnet_object = {
        'id': entry['info_hash'],
        'title': entry['name'],
        'magnet_link': magnet_link,
        'command_msg': f"/start {entry['info_hash']} {search_phrase}",
        'description': f"Uploaded:{uploaded_date} | Size:{size_human} | Seeders: {entry['seeders']} | Leechers: {entry['leechers']}",
        # Full metadata for persistence
        'size_bytes': size_bytes,
        'size_human': size_human,
        'seeders': int(entry['seeders']),
        'leechers': int(entry['leechers']),
        'uploaded_date': uploaded_date.isoformat(),  # ISO format string for JSON serialization
    }
    return magnet_object


class TpbAdaptor:
    def __init__(self, logger):
        self.logger = logger

    def fetch_magnet_links(self, phrases: list[str], limit: int = 10):
        """ Returns array of [{btih_article}, {btih_article},] """

        search_phrase = phrases.replace(' ', '+')
        self.logger.debug(f'Looking up: {search_phrase}')
        magnet_objects = []
        search_path = f'{os.environ.get("SEARCH_URL")}{search_phrase}'

        user_agent = {'User-Agent': os.environ.get('USER_AGENT')}
        http = urllib3.PoolManager(headers=user_agent)
        r1 = http.request('GET', search_path)

        # For Debug purposes #1
        # r1 = MockR()

        if r1.status != 200:
            self.logger.debug(search_path)
            self.logger.debug(r1.status)
            # self.logger.debug(r1.data)
            self.logger.debug(r1.data.decode())
        else:
            # For Debug purposes #2
            # tmp_path = "./tmp/response_body"
            # tmp_file = open(tmp_path, 'wb')
            # tmp_file.write(r1.data)
            # tmp_file.close()
            parsed_result = json.loads(r1.data.decode())

            for entry in parsed_result[1: 1 + limit]:
                magnet_objects += [get_magnet_details(entry, search_phrase)]

        return magnet_objects


# class MockR:
#     # For Debug purposes #3
#     def __init__(self):
#         tmp_path = "./tmp/response_body"
#         tmp_file = open(tmp_path, 'rb')
#         self.data = tmp_file.read()
#         tmp_file.close()
#         self.status = 200
