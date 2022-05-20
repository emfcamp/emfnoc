import os
import sys
from configparser import ConfigParser


class EmfNoc:

    _config: ConfigParser = None

    @staticmethod
    def load_config():
        if EmfNoc._config:
            return EmfNoc._config

        files = ['emfnoc.conf', '~/.emfnoc.conf', '/etc/emfnoc.conf']
        for file in files:
            if os.path.exists(file):
                config = ConfigParser()
                if config.read(file):
                    EmfNoc._config = config
                    return EmfNoc._config
                else:
                    print("Warning: %s found but could not be loaded" % file, file=sys.stderr)

        print("No emfnoc config file could be read, looked in " + str(files), file=sys.stderr)
        sys.exit(1)
