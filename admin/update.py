#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys

sys.path.insert(0,os.path.dirname('..'))

from int_service.lib.dataworker import UpdateWorker

def main():
    data_worker = UpdateWorker()
    data_worker.update_data()

if __name__ == "__main__":
    main()