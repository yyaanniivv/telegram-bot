import os
import re
import time

# Torrent file creator


def extract_btih(text):
    pattern = re.compile('magnet:\\?xt=urn:btih:([^&/]+)')
    matches = pattern.match(text)
    return matches.groups(1)[0]


class TorrentFile:
    def __init__(self, start_args: list[str], logger):
        self.logger = logger
        self.info_hash = start_args[0]
        self.search_term = ''.join(start_args[1:])

    def create(self):
        btih = self.info_hash if len(
            self.info_hash) == 40 else extract_btih(self.info_hash)
        date = str(round(time.time()))
        if btih:
            file_name = f'bot-{date}-{self.search_term}.torrent'
            output_path = os.path.join(os.environ.get('OUTPUT_DIR'),
                                       file_name)
            torrent_file = open(output_path, 'w+')
            # TODO: test and remove this
            # torrent_file.write('d10:magnet-uri' + str(len(btih)) + ':' + btih + 'e')
            torrent_file.write(f'd10:magnet-uri{str(len(btih))}:{btih}e')
            torrent_file.close()
            self.logger.info('Created file: ' + output_path)
            return file_name
        else:
            self.logger.info('No magnet matched. :-(')
            return
