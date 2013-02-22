Интеграционный сервер (ИС)
=================

Интеграционный сервер обеспечивает взаимодействие между различными ТМИС.
Для установки ИС ознакомьтесь с системными требованиями и инструкцией, указанными ниже.

Системные требования
-----------

* Python 2.7
* MySQL 5 (http://dev.mysql.com/downloads/installer/)
* Web-Server Apache (http://httpd.apache.org/download.cgi) + mod_wsgi (http://code.google.com/p/modwsgi/wiki/DownloadTheSoftware)
* git
* zlib

Установка
-----------
* Установить MySQL
* Установить Apache
* Скачать модуль mod_wsgi, скопиррвать в директорию модулей Apache2/modules, подключить модуль в конфиге Apache2/conf/httpd.conf:
```
LoadModule mod_wsgi modules/mod_wsgi.so
```

