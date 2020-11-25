from dotenv import load_dotenv
from os.path import dirname, join, os
import time

# TpbAdator
import urllib3
import json

# Load .env params:
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

#  scraper maybe inhert a interface which will have: #get_articles
#  TODO: magnet_object will have to_string, to_article, to_json


def create_magnet_link(info_hash):
    return os.environ.get('MAGNET_PREFIX') + info_hash + os.environ.get('MAGNET_SUFFIX')


def get_magnet_details(entry):
    date = time.strftime('%Y-%m-%d', time.localtime(int(entry['added'])))
    size = str(round(int(entry["size"]) / 1024**2, 2)) + 'Mib'  # Size in MiB
    description_object = {
        'uploaded': date,
        'size': size,
        'seeders ^': entry['seeders'],
        'leachers v': entry['leechers'],
    }
    magnet_object = {
        'id': entry['info_hash'],
        'title': entry['name'],
        'command_msg': f"/start {create_magnet_link(entry['info_hash'])}",
        'description': ' | '.join('{}:{}'.format(key.capitalize(), val) for key, val in description_object.items()),
    }
    return magnet_object


class TpbAdaptor:
    def __init__(self, logger):
        self.logger = logger

    def search(self, term):
        print(term)

    def request_magnet_links(self, search_phrase: list[str], limit: int = 10):
        # Returns array of magnet objects
        # returns [{magnet_object}, {magnet_object},]

        magnet_objects = []
        search_path = os.environ.get('SEARCH_URL') + \
            search_phrase.replace(' ', '+')

        user_agent = {'User-Agent': os.environ.get('USER_AGENT')}
        http = urllib3.PoolManager(headers=user_agent)
        # r1 = http.request('GET', search_path)

        r1 = MockR()

        if r1.status != 200:
            self.logger.debug(search_path)
            self.logger.debug(r1.status)
            # self.logger.debug(r1.data)
            self.logger.debug(r1.data.decode())
        else:
            # tmp_path = "./tmp_response_body"
            # tmp_file = open(tmp_path, 'wb+')
            # tmp_file.write(r1.data)
            # tmp_file.close()
            parsed_result = json.loads(r1.data.decode())

            for entry in parsed_result[1: 1 + limit]:
                magnet_objects += [get_magnet_details(entry)]

        return magnet_objects


class MockR:
    def __init__(self):
        tmp_path = "./tmp_response_body"
        tmp_file = open(tmp_path, 'rb')
        self.data = tmp_file.read()
        tmp_file.close()
        self.status = 200
