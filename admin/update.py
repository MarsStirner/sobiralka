#!/usr/bin/env python
# -*- coding: utf-8 -*-

from int_service.lib.dataworker import UpdateWorker

def main():
    data_worker = UpdateWorker()
    data_worker.update_data()

if __name__ == "__main__":
    main()