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

Настройка серверного окружения
-----------

* Конфигурирование Apache (Apache2/conf/httpd.conf), секция Virtual Hosts:

Конфигурирация для ИС:

```
Listen %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%
<VirtualHost %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%>
    ServerName %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%
    DocumentRoot "%PROJECT_ROOT%"

    ErrorLog logs/%PROJECT_NAME%-error.log
    CustomLog logs/%PROJECT_NAME%-access.log common
    LogLevel warn

    WSGIProcessGroup %PROJECT_NAME%
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
Listen %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%
<VirtualHost %SOAP_SERVER_HOST%:%SOAP_SERVER_PORT%>
        ServerName %SOAP_ADMIN_HOST%:%SOAP_SERVER_PORT%
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
%SOAP_SERVER_PORT% - порт, по которому будет вестись обращение к ИС (например, 80)
%PROJECT_ROOT% - директория, где располагаются файлы проекта (в нашем примере, D:/projects/int_server)
%PROJECT_NAME% - название проекта (например, int_server)
%PROJECT_CODE_ROOT% - директория, где располагается код проекта (в нашем примере, D:/projects/int_server/code)
```



