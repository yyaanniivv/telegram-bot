# Bot logic
import logging
TELEGRAM_LOGGER = "TelegramBot"
logger = logging.getLogger("TelegramBot")


class Scraper:
    #  scraper maybe inhert a interface which will have: #get_articles
    #  magnet_object will have to_string, to_article, to_json
    @staticmethod
    def get_magnet_details(row):
        uploaded_n_size = row.find('font', {'class': 'detDesc'}).text.replace(u'\xa0', ' ').split(',').pop()
        seed_n_leech = row.find_all('td', {'align': 'right'})
        description_object = {
            'uploaded': uploaded_n_size[0].strip(),
            'size': uploaded_n_size[1].strip(),
            'comments': row.find('img', {'src': 'https://tpb.party/static/img/icon_comment.gif'}).get('alt'),
            'seeders ^': seed_n_leech[0].text.strip(),
            'leachers v': seed_n_leech[1].text.strip(),
        }

        description_string = ' | '.join('{}:{}'
                                  .format(key.capitalize(), val) for key, val in description_object.items())
        magnet_object = {
            'title': row.find('div', {'class': 'detName'}).text.strip(),
            'magnet_link': row.find('a', {'title': 'Download this torrent using magnet'}).get('href'),  # this will be sent back to the bot.
            'description': description_string,
        }
        return magnet_object

    # Returns array of magnet objects
    # returns [{magnet_object}, {magnet_object},]
    def request_magnet_links(search_phrase):
        # limit = os.environ.get('LIMIT') || 25 # consider using limit
        search_path = os.environ.get('SEARCH_URL') + search_phrase.replace(' ', '%20')
        user_agent = {'User-Agent': os.environ.get('USER_AGENT')}
        magnet_objects = []

        http = urllib3.PoolManager(headers=user_agent)
        r1 = http.request('GET', search_path)

        if r1.status != 200:
            logger.info('fetch failed')
            logger.info(search_path)
            logger.info(r1.status)
            logger.info(r1.data)
            return
        else:
            logger.info('fetch success')
            soup = BeautifulSoup(html_str, 'html.parser')

            # exists even if the result set is empty.
            # first row is headers, last is navigation.
            result_table = soup.find_all('table', {'id': 'searchResult'})[0]
            number_of_results = len(result_table)
            if number_of_results > 1:
                for row in result_table[1: number_of_results - 1]:  # consider using LIMIT
                    magnet_objects += [Scraper.get_magnet_details(row)]
            return magnet_objects
