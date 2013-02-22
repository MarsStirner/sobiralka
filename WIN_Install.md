Интеграционный сервер (ИС)
=================

Интеграционный сервер обеспечивает взаимодействие между различными ТМИС.
Для установки ИС ознакомьтесь с системными требованиями и инструкцией, указанными ниже.

Системные требования
-----------

* Python 2.7 (http://www.python.org/download/)
* MySQL 5 (http://dev.mysql.com/downloads/installer/)
* Web-Server Apache (http://httpd.apache.org/download.cgi) + mod_wsgi (http://code.google.com/p/modwsgi/wiki/DownloadTheSoftware)
* git (http://git-scm.com/download/win)

Установка
-----------
* Установить MySQL
* Установить Apache
* Скачать модуль mod_wsgi, скопиррвать в директорию модулей Apache2/modules, подключить модуль в конфиге Apache2/conf/httpd.conf:

```
LoadModule mod_wsgi modules/mod_wsgi.so
```
* Установить Python и прописать его в системный путь (например, через cmd):

```
set PATH=%PATH%;D:\Python27;D:\Python27\Scripts
```

* Установить setup_tools (http://peak.telecommunity.com/dist/ez_setup.py)

```
python \путь\до\ez_setup.py
```

* Установить pip

```
easy_install.exe pip
```

* Создать директорию проекта, например D:\projects\int_server и перейти в неё в консоли:

```
cd D:\projects\int_server
```

* Установить virtualenv, создать и активировать виртуальную среду

```
pip install virtualenv
virtualenv venv
venv\Scripts\activate
```

* Клонировать репозиторий из git, для этого в директории проекта вызвать из контекстного меню Git Bash и выполнить команду:

```
git clone https://github.com/KorusConsulting/sobiralka.git code
```

* Установить зависимости через командную строку:

```
pip install -r code\requirements.txt
```
