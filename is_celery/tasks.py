# -*- coding: utf-8 -*-
from __future__ import absolute_import

from is_celery.celery_init import celery
from int_service.lib.dataworker import EPGUWorker

epgu_dw = EPGUWorker()
epgu_dw.sync_schedule_task.delay()