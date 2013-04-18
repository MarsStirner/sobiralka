# -*- coding: utf-8 -*-
from __future__ import absolute_import
from celery import Celery
from settings import DB_CONNECT_STRING

celery = Celery('is_celery')

celery.conf.update(
    BROKER_URL='sqla+%s' % DB_CONNECT_STRING,
    CELERY_RESULT_BACKEND="database",
    CELERY_RESULT_DBURI=DB_CONNECT_STRING,
    # CELERY_TASK_SERIALIZER = 'json'
    # CELERY_RESULT_SERIALIZER='json',
    CELERY_TIMEZONE='Europe/Moscow',
    CELERY_ENABLE_UTC=True,
    # CELERY_IMPORTS=("is_celery.tasks", ),
    CELERY_INCLUDE=('int_service.lib.dataworker', ),
    # CELERY_SEND_TASK_ERROR_EMAILS = True
    # ADMINS = (('Admin', 'admin@localhost'), )
    CELERYD_MAX_TASKS_PER_CHILD=5,
    CELERY_TASK_RESULT_EXPIRES=3600,

)

if __name__ == '__main__':
    celery.start()