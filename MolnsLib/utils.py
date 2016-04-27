import os
import logging

from MolnsLib.constants import Constants


class Logger(object):

    def __init__(self, name):
        name = name.replace('.log','')
        logger = logging.getLogger('MOLNS.%s' % name)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            file_name = os.path.join(Constants.LOGGING_DIRECTORY, '%s.log' % name)
            handler = logging.FileHandler(file_name)
            formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s %(message)s')
            handler.setFormatter(formatter)
            handler.setLevel(logging.DEBUG)
            logger.addHandler(handler)
        self._logger = logger

    def get(self):
        return self._logger