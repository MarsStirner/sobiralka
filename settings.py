# -*- coding: utf-8 -*-
DB_HOST = 'localhost:3306'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'soap'
SYSTEM_USER = 'is_user'

SOAP_SERVER_HOST = '127.0.0.1'
SOAP_SERVER_PORT = 9910
SOAP_ADMIN_HOST = '127.0.0.1'

#SOAP_NAMESPACE = 'urn:ru.gov.economy:std.ws'
SOAP_NAMESPACE = 'tns'
FLASK_SECRET_KEY = ''

from settings_local import *

DB_CONNECT_STRING = 'mysql://' + DB_USER + ':' + DB_PASSWORD + '@' + DB_HOST + '/'+ DB_NAME +'?charset=utf8'