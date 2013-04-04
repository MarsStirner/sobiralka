# -*- coding: utf-8 -*-
from settings import DB_CONNECT_STRING

BROKER_URL = 'sqla+%s' % DB_CONNECT_STRING

CELERY_RESULT_BACKEND = "database"
CELERY_RESULT_DBURI = DB_CONNECT_STRING

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Moscow'
CELERY_ENABLE_UTC = True

CELERY_IMPORTS = ("async.tasks", )