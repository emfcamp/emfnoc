import os
import sys

from typing import Optional

from configparser import ConfigParser

import logging


_LOGGER = logging.getLogger(__name__)

class EmfNoc:

    _config: Optional[ConfigParser] = None

    @classmethod
    def load_config(cls) -> ConfigParser:
        if cls._config:
            return cls._config

        files = ['emfnoc.conf', '~/.emfnoc.conf', '/etc/emfnoc.conf']
        for file in files:
            file = os.path.expanduser(file)
            if os.path.exists(file):
                config = ConfigParser()
                if config.read(file):
                    cls._config = config
                    return cls._config
                else:
                    _LOGGER.warning("%s found but could not be loaded", file)

        raise RuntimeError('No emfnoc config file could be read, looked in ' + str(files))
