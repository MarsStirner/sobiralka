# -*- coding: utf-8 -*-
from __future__ import absolute_import
from celery import Celery
from celery.schedules import crontab
from settings import DB_CONNECT_STRING, DEBUG

celery = Celery('is_celery')

celery.conf.update(
    BROKER_URL='sqla+%s' % DB_CONNECT_STRING,
    CELERY_RESULT_BACKEND="database",
    CELERY_RESULT_DBURI=DB_CONNECT_STRING,
    CELERY_RESULT_ENGINE_OPTIONS={"echo": DEBUG},
    # CELERY_TASK_SERIALIZER = 'json'
    # CELERY_RESULT_SERIALIZER='json',
    CELERY_TIMEZONE='Europe/Moscow',
    CELERY_ENABLE_UTC=True,
    CELERY_DISABLE_RATE_LIMITS=True,
    # CELERY_IMPORTS=("is_celery.tasks", ),
    CELERY_INCLUDE=('is_celery.tasks', ),
    # CELERY_SEND_TASK_ERROR_EMAILS = True
    # ADMINS = (('Admin', 'admin@localhost'), )
#    CELERYD_MAX_TASKS_PER_CHILD=5,
    CELERY_TASK_RESULT_EXPIRES=172800,
    CELERY_DEFAULT_DELIVERY_MODE = 'transient',
)

celery.conf.update(
    CELERYBEAT_SCHEDULE={
        'update_db_every_3_hours': {
            'task': 'is_celery.tasks.update_db',
            'schedule': crontab(minute=0, hour='6,9,12,15,18,21'),
        },
        'periodical_sync_locations': {
            'task': 'is_celery.tasks.sync_locations',
            'schedule': crontab(minute=10, hour=0, day_of_week=0),
        },
        'periodical_sync_schedules': {
            'task': 'is_celery.tasks.sync_schedule_task',
            'schedule': crontab(minute=0, hour=1, day_of_week=0),
        },
        'periodical_clear_broker': {
            'task': 'is_celery.tasks.clear_broker_messages',
            'schedule': crontab(minute=0, hour=1, day_of_week=6),
        },
    }
)

if __name__ == '__main__':
    celery.start()