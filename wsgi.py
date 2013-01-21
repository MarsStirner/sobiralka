# -*- coding: utf-8 -*-
import os, sys
from int_service.lib.soap_server import Server


sys.path.insert(0,os.path.dirname(__file__))

server = Server()
application = server.applications