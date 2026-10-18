import os
import re
import time


# BTIH: 40 hex characters (SHA1 hash)
BTIH_PATTERN = re.compile(r'^[a-fA-F0-9]{40}$')
# Magnet link: magnet:?xt=urn:btih:<40 hex chars>
MAGNET_PATTERN = re.compile(r'^magnet:\?xt=urn:btih:[a-fA-F0-9]{40}(?:&.*)?$')


def extract_btih(text):
    pattern = re.compile('magnet:\\?xt=urn:btih:([^&/]+)')
    matches = pattern.match(text)
    if matches:
        return matches.groups(1)[0]
    return None


def validate_btih(btih: str) -> bool:
    """Validate BTIH is 40 hex characters."""
    return bool(BTIH_PATTERN.match(btih))


def validate_magnet(magnet: str) -> bool:
    """Validate magnet link format."""
    return bool(MAGNET_PATTERN.match(magnet))


def validate_input(input_str: str) -> tuple[bool, str]:
    """
    Validate input is either a valid BTIH or magnet link.
    Returns (is_valid, input_type) where input_type is 'btih', 'magnet', or 'invalid'.
    """
    if validate_btih(input_str):
        return True, 'btih'
    if validate_magnet(input_str):
        return True, 'magnet'
    return False, 'invalid'


class TorrentFile:
    """ Accepts a magnet link or btih and outputs a torrent file."""

    def __init__(self, start_args: list[str], logger):
        self.logger = logger
        # Note: Could also be btih
        self.magnet = start_args[0]
        self.search_term = ''.join(start_args[1:])

    def is_btih(self):
        """ Naively assert that the btih is valid. """
        return validate_btih(self.magnet)

    def create(self):
        date = str(round(time.time()))

        # Validate input
        is_valid, input_type = validate_input(self.magnet)
        if not is_valid:
            self.logger.warning(
                f'Invalid input rejected: {self.magnet[:50]}... (type: {input_type})'
            )
            return

        if input_type == 'btih':
            self.logger.info(f'Got btih: {self.magnet}. Wrapping it up!')
            prefix = os.environ.get('MAGNET_PREFIX')
            suffix = os.environ.get('MAGNET_SUFFIX')
            self.magnet = f"{prefix}{self.magnet}{suffix}"
        else:  # magnet
            self.logger.info('Got magnetlink.')

        file_name = f'bot-{date}-{self.search_term}.torrent'
        output_path = os.path.join(os.environ.get('OUTPUT_DIR'),
                                   file_name)
        torrent_file = open(output_path, 'w+')
        torrent_file.write(
            f'd10:magnet-uri{str(len(self.magnet))}:{self.magnet}e')
        torrent_file.close()

        # Configurable file ownership (skip on non-Linux or if not set)
        uid = os.environ.get('OUTPUT_UID')
        gid = os.environ.get('OUTPUT_GID')
        if uid and gid and hasattr(os, 'chown'):
            try:
                os.chown(output_path, int(uid), int(gid))
                self.logger.debug(f'Changed ownership to {uid}:{gid}')
            except (PermissionError, OSError) as e:
                self.logger.warning(f'Failed to chown {output_path}: {e}')
        else:
            self.logger.debug('Skipping chown (OUTPUT_UID/GID not set or unsupported platform)')

        self.logger.info(f'Created file: {output_path}')
        return file_name
