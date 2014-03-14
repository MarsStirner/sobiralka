# -*- coding: utf-8 -*-
from pysimplelogs.logger import SimpleLogger
import pprint


class MyPrettyPrinter(pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        if isinstance(object, unicode):
            return (object.encode('utf8'), True, False)
        return pprint.PrettyPrinter.format(self, object, context, maxlevels, level)


from settings import DEBUG, SIMPLELOGS_URL
from version import version
logger = SimpleLogger.get_logger(SIMPLELOGS_URL,
                                 'IS',
                                 dict(name='IS', version=version),
                                 DEBUG)