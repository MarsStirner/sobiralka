# -*- coding: utf-8 -*-
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'soap'
SYSTEM_USER = 'is_user'

SOAP_SERVER_HOST = '127.0.0.1'
SOAP_SERVER_PORT = 9910
SOAP_ADMIN_HOST = '127.0.0.1'

TFOMS_SERVICE_HOST = '127.0.0.1'
TFOMS_SERVICE_PORT = 5500
TFOMS_SERVICE_USER = 'tfoms'
TFOMS_SERVICE_PASSWORD = 'tfoms'

#SOAP_NAMESPACE = 'urn:ru.gov.economy:std.ws'
SOAP_NAMESPACE = 'tns'
FLASK_SECRET_KEY = ''

EPGU_SERVICE_URL = ''

from settings_local import *

DB_CONNECT_STRING = 'mysql://%s:%s@%s:%s/%s?charset=utf8' % (DB_USER , DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)