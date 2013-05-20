#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('.'))

from int_service.lib.dataworker import UpdateWorker
from admin.database import init_db


def main():
    init_db()
    data_worker = UpdateWorker()
    data_worker.update_data()

if __name__ == "__main__":
    main()