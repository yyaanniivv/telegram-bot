import os
import re
import time


def extract_btih(text):
    pattern = re.compile('magnet:\\?xt=urn:btih:([^&/]+)')
    matches = pattern.match(text)
    return matches.groups(1)[0]


class TorrentFile:
    """ Accepts a magnet link and outputs a torrent file."""

    def __init__(self, start_args: list[str], logger):
        self.logger = logger
        self.magnet = start_args[0]
        self.search_term = ''.join(start_args[1:])

    def create(self):
        btih = extract_btih(self.magnet)
        date = str(round(time.time()))
        # Naively assert that the btif is valid.
        if len(btih) == 40:
            file_name = f'bot-{date}-{self.search_term}.torrent'
            output_path = os.path.join(os.environ.get('OUTPUT_DIR'),
                                       file_name)
            torrent_file = open(output_path, 'w+')
            # TODO: test and remove this
            # torrent_file.write('d10:magnet-uri' +
            #                    str(len(self.magnet)) + ':' + self.magnet + 'e')
            torrent_file.write(
                f'd10:magnet-uri{str(len(self.magnet))}:{self.magnet}e')
            torrent_file.close()
            os.chown(output_path, 1000, 1000)
            self.logger.info('Created file: ' + output_path)
            return file_name
        else:
            self.logger.info('No magnet matched. :-(')
            return
