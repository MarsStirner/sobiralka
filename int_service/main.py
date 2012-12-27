# -*- coding: utf-8 -*-
import os
import sys

root_path = os.path.abspath(os.path.split(__file__)[0])
sys.path.insert(0, os.path.join(root_path, 'int_service'))
sys.path.insert(0, root_path)

from lib.soap_server import Server

def main():
    Server.run()

if __name__ == "__main__":
    main()