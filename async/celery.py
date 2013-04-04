# -*- coding: utf-8 -*-
from __future__ import absolute_import

from celery import Celery

celery = Celery('async.celery')

celery.config_from_object('celeryconfig')

if __name__ == '__main__':
    celery.start()