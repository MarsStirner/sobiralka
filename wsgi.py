# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from int_service.lib.soap_server import Server

server = Server()
application = server.applications