#!/usr/bin/env python
# -*- coding: utf-8 -*-

from int_service.lib.soap_server import Server

def main():
    server = Server()
    server.run()

if __name__ == "__main__":
    main()