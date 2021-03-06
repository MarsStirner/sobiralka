Интеграционный сервер (ИС)
=================

Интеграционный сервер обеспечивает взаимодействие между различными ТМИС.
Для установки ИС ознакомьтесь с системными требованиями и инструкцией, указанными ниже.

Системные требования
-----------

* ОС Windows
* Python 2.7 (http://www.python.org/download/)
* MySQL 5 (http://dev.mysql.com/downloads/installer/)
* Web-Server Apache2.2 (http://www.sai.msu.su/apache/dist/httpd/binaries/win32/) + mod_wsgi (http://code.google.com/p/modwsgi/wiki/DownloadTheSoftware)
* git (http://git-scm.com/download/win)
* Twisted (http://twistedmatrix.com/Releases/Twisted/12.3/Twisted-12.3.0.win32-py2.7.msi)

Под windows используются только 32-bit версии

Установка
-----------
* Установить MySQL

При конфигурировании MySQL, рекомендуется установить в my.cnf:

```
lower_case_table_names=2
```
* Создать новую БД, например с именем: soap.
* Установить Apache
* Скачать модуль mod_wsgi, скопиррвать в директорию модулей Apache2.2/modules, подключить модуль в конфиге Apache2.2/conf/httpd.conf:

```
LoadModule mod_wsgi modules/mod_wsgi.so
```

* Установить Python и прописать его в системный путь (например, через cmd):

```
set PYTHONPATH=%PYTHONPATH%;D:\Python27;D:\Python27\Scripts
set PATH=%PATH%;%PYTHONPATH%
```
* Установить Twisted (http://twistedmatrix.com/Releases/Twisted/12.3/Twisted-12.3.0.win32-py2.7.msi)

* Установить setup_tools (https://pypi.python.org/pypi/setuptools/0.6c11#downloads)

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

* Установить MySQL-python 

```
 easy_install MySQL-python
```

* Установить lxml (http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml)
 
* Клонировать репозиторий из git, для этого в директории проекта вызвать из контекстного меню Git Bash и выполнить команду:

```
git clone https://github.com/KorusConsulting/sobiralka.git code
```

* Установить зависимости через командную строку:

```
pip install -r code\requirements.txt
```

Настройка серверного окружения
-----------

* Конфигурирование виртуальных хостов Apache (Apache2.2/conf/extra/httpd-vhosts.conf), секция Virtual Hosts, добавить следующие конфигурации:

Конфигурирация для ИС:

```
Listen %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%
<VirtualHost %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%>
    ServerName %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%
    DocumentRoot "%PROJECT_ROOT%"

    ErrorLog logs/%PROJECT_NAME%-error.log
    CustomLog logs/%PROJECT_NAME%-access.log common
    LogLevel warn
    
    WSGIScriptAlias / "%PROJECT_CODE_ROOT%/wsgi.py"

    <Directory "%PROJECT_ROOT%/">
        AllowOverride All
        Options None
        Order allow,deny
        Allow from all
    </Directory>
</VirtualHost>

WSGIPythonOptimize 2
```

Конфигурация для административного интерфейса ИС:

```
Listen %SOAP_ADMIN_HOST%:%SOAP_ADMIN_PORT%
<VirtualHost %SOAP_ADMIN_HOST%:%SOAP_ADMIN_PORT%>
        ServerName %SOAP_ADMIN_HOST%:%SOAP_ADMIN_PORT%
        DocumentRoot "%PROJECT_ROOT%"
        
        ErrorLog logs/admin.%PROJECT_NAME%-error.log
        CustomLog logs/admin.%PROJECT_NAME%-access.log common
        LogLevel warn
        
        WSGIScriptAlias / "%PROJECT_CODE_ROOT%/admin/wsgi.py"
</VirtualHost>
```

где:

```
%SOAP_SERVER_HOST% - хост, по которому будет вестись обращение к ИС (как вариант - IP сервера)
%SOAP_SERVER_PORT% - порт, по которому будет вестись обращение к ИС (например, 9910)
%PROJECT_ROOT% - директория, где располагаются файлы проекта (в нашем примере, D:/projects/int_server)
%PROJECT_NAME% - название проекта (например, int_server)
%PROJECT_CODE_ROOT% - директория, где располагается код проекта (в нашем примере, D:/projects/int_server/code)
```

* Настройка конфига ИС

Необходимо переопределить константы в файле settings_local.py в корне ИС:

```
#Параметры подключения к БД
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'soap_user'
DB_PASSWORD = 'q1w2e3r4t5'
DB_NAME = 'soap'

#Системный пользователь, от которого будет запускаться вэб-сервер
SYSTEM_USER = 'is_user'

#Хост и порт, по которым будет доступен ИС
SOAP_SERVER_HOST = '127.0.0.1'
SOAP_SERVER_PORT = 9910
```
Параметры подключения к БД соответствуют параметрам, установленным при создании БД для ИС.

SOAP_SERVER_HOST и SOAP_SERVER_PORT - должны соответствовать %SOAP_SERVER_HOST% и %SOAP_SERVER_PORT%, указанным в конфиге апача

* Перезапустить Apache для того, чтобы конфиг вступил в силу
* Создать таблицы БД, выполнив:

```
cd code
python admin\update.py
```

* Открыть в браузере административный интерфейс ИС (http://%SOAP_ADMIN_HOST%:%SOAP_ADMIN_PORT%/admin/) и настроить список регионов и КС, с которыми будет работать ИС.
* Создать таблицы БД, выполнив:

```
python admin\update.py
```

* Добавить активацию виртуального окружения в начало файлов wsgi.py и в admin\wsgi.py:

```
# -*- coding: utf-8 -*-
activate_this = '%PROJECT_ROOT%/venv/Scripts/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
```

* Настроить Регионы и КС ЛПУ, с которыми будет работать ИС через административный интерфейс:

http://%SOAP_ADMIN_HOST%:%SOAP_ADMIN_PORT%/admin/

* Проапдейтить таблицы БД данными из указанных КС, выполнив:

```
python admin\update.py
```
