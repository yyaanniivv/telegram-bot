import os
import re
import time


def extract_btih(text):
    pattern = re.compile('magnet:\\?xt=urn:btih:([^&/]+)')
    matches = pattern.match(text)
    return matches.groups(1)[0]


class TorrentFile:
    """ Accepts a magnet link or btih and outputs a torrent file."""

    def __init__(self, start_args: list[str], logger):
        self.logger = logger
        # Note: Could also be btih
        self.magnet = start_args[0]
        self.search_term = ''.join(start_args[1:])

    def is_btih(self):
        """ Naively assert that the btif is valid. """
        return len(self.magnet) == 40

    def create(self):
        date = str(round(time.time()))

        if(self.is_btih()):
            self.logger.info(f'Got btih: {self.magnet}. Wrapping it up!')
            self.magnet = f"{os.environ.get('MAGNET_PREFIX')}{self.magnet}{os.environ.get('MAGNET_SUFFIX')}"
        elif(len(self.magnet) > 40):  # and extract_btih(text) works
            self.logger.info(f'Got magnetlink.')
        else:
            self.logger.info(f'No matche. :-( {self.magnet}')
            return

        file_name = f'bot-{date}-{self.search_term}.torrent'
        output_path = os.path.join(os.environ.get('OUTPUT_DIR'),
                                   file_name)
        torrent_file = open(output_path, 'w+')
        torrent_file.write(
            f'd10:magnet-uri{str(len(self.magnet))}:{self.magnet}e')
        torrent_file.close()
        os.chown(output_path, 1000, 1000)
        self.logger.info(f'Created file: {output_path}')
        return file_name
