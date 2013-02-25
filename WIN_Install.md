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
* Скачать модуль mod_wsgi, скопиррвать в директорию модулей Apache2/modules, подключить модуль в конфиге Apache2/conf/httpd.conf:

```
LoadModule mod_wsgi modules/mod_wsgi.so
```

* Установить Python и прописать его в системный путь (например, через cmd):

```
set PATH=%PATH%;D:\Python27;D:\Python27\Scripts
```

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

* Конфигурирование Apache (Apache2/conf/httpd.conf), секция Virtual Hosts, добавить следующие конфигурации:

Конфигурирация для ИС:

```
Listen %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%
<VirtualHost %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%>
    ServerName %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%
    DocumentRoot "%PROJECT_ROOT%"

    ErrorLog logs/%PROJECT_NAME%-error.log
    CustomLog logs/%PROJECT_NAME%-access.log common
    LogLevel warn
    
    WSGIPythonHome %PROJECT_ROOT%/venv/
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
        
        WSGIPythonHome %PROJECT_ROOT%/venv/
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
