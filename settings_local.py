# -*- coding: utf-8 -*-

DEBUG = True

#Параметры подключения к БД
DB_HOST = '192.168.1.121'
DB_PORT = 3306
DB_USER = 'tmis'
DB_PASSWORD = 'q1w2e3r4t5'
DB_NAME = 'soap'

#Системный пользователь, от которого будет запускаться вэб-сервер
SYSTEM_USER = 'is_user'

#Хост и порт, по которым будет доступе ИС
SOAP_SERVER_HOST = '127.0.0.1'
SOAP_SERVER_PORT = 9910

#Хост, по которому будет доступен административный интерфейс ИСа
SOAP_ADMIN_HOST = '127.0.0.1'

FLASK_SECRET_KEY = 'ohp%)%6vyq05mr2sc#rb$oe@we&$un534**tb04#^z99iq)(y='