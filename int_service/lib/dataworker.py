# -*- coding: utf-8 -*-
import exceptions
import sys

try:
    import json
except ImportError:
    import simplejson as json

from settings import DEBUG
logger_tags = dict(tags=['dataworker', 'IS'])

import logging

h1 = logging.StreamHandler(sys.stdout)
rootLogger = logging.getLogger()
rootLogger.addHandler(h1)

if DEBUG:
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
else:
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)


class DataWorker(object):
    """Provider class for current DataWorkers"""
    @classmethod
    def provider(cls, data_type, *args, **kwargs):
        """Вернёт объект для работы с указанным типом данных"""
        data_type = data_type.lower()
        if data_type == 'regions':
            obj = RegionsWorker()
        elif data_type == 'lpu':
            obj = LPUWorker(*args, **kwargs)
        elif data_type == 'lpu_units':
            obj = LPU_UnitsWorker()
        elif data_type == 'enqueue':
            obj = EnqueueWorker(*args, **kwargs)
        elif data_type == 'personal':
            obj = PersonalWorker()
        elif data_type == 'epgu':
            obj = EPGUWorker(*args, **kwargs)
        else:
            obj = None
            raise exceptions.NameError
        return obj


from workers.lpu import LPUWorker
from workers.departments import LPU_UnitsWorker
from workers.person import PersonalWorker
from workers.enqueue import EnqueueWorker
from workers.regions import RegionsWorker
from workers.update import UpdateWorker
from workers.epgu import EPGUWorker