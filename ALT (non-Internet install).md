Интеграционный сервер (ИС)
=================

Интеграционный сервер обеспечивает взаимодействие между различными ТМИС.
Для установки ИС ознакомьтесь с системными требованиями и инструкцией, указанными ниже.

Системные требования
-----------

* ОС AltLinux

### Необходимое ПО, поставляемое с дистрибутивом AltLinux

* Python 2.6 и выше
* Web-Server Apache2 + apache2-mod_wsgi
* zlib

### Устанавливаемое ПО

**Update системы**

```
apt-get update
apt-get upgrade
```

* C-compiler (gcc) ```apt-get install gcc4.4``` (установить подходящую версию, в данном случае 4.4)
 * binutils
 * cpp4.4
 * gcc-common
 * glibc
 * glibc-devel
 * glibc-kernheaders
 * glibc-timezones
 * kernel-headers-common
 * libmprf
 * tzdata
* MySQL 5 (MySQL-server, MySQL-client) ```apt-get install MySQL-server``` ```apt-get install MySQL-client```
* python-module-MySQLdb ```apt-get install python-module-MySQLdb```
* libxml2-devel ```apt-get install libxml2-devel```
* libxslt-devel ```apt-get install libxslt-devel```
 * libxslt
* libmysqlclient-devel ```apt-get install libmysqlclient-devel```


**Во вложенных пунктах указаны зависимости, которые потребуется разрешить**


Установка ИС
-----------

Описанная ниже установка и настройка ПО производится из консоли Linux. Используется root-доступ.


### Установка и настройка виртуального окружения, библиотек Python

```
apt-get install python-module-virtualenv
```

Используем директорию /srv/ для обеспечения защищенной установки ИС. Вместо /srv можно использовать любую удобную директорию на сервере (например, /var/www/webapps).

При этом, следуя инструкции, необходимо подразумевать, что вместо /srv необходимо указывать Вашу директорию.

В качестве имени проекта (my_project) можно использовать произвольное.

```
cd /srv/my_project
```

#### Установка python-модулей в виртуальное окружение

**Создание и активация виртуального окружения**

```
virtualenv .virtualenv
source .virtualenv/bin/activate
```

**Общий принцип установки python-модулей**

* Заливаем во временную директорию (например /srv/my_project/tmp) архив модуля, скаченный с https://pypi.python.org/
* Распаковываем архив и переходим в директорию модуля 
 * ```tar xvfz *.tar.gz``` или ```unzip *.zip```
 * ```cd unpacked_module_dir```
* Выполняем ```python setup.py install```

**Перечень модулей для установки**

* fabric (https://pypi.python.org/pypi/Fabric/)
 * pycrypto>=2.6 (https://pypi.python.org/pypi/pycrypto/)
 * paramiko>=1.10.1 (https://pypi.python.org/pypi/paramiko/)
* Flask (https://pypi.python.org/pypi/Flask/)
 * Jinja2>=2.4 (https://pypi.python.org/pypi/Jinja2/)
 * Werkzeug>=0.7 (https://pypi.python.org/pypi/Werkzeug/)
* WTForms (https://pypi.python.org/pypi/WTForms/)
* Flask-WTF (https://pypi.python.org/pypi/Flask-WTF/)
* Flask-Admin (https://pypi.python.org/pypi/Flask-Admin/)
* Flask-BabelEx (https://pypi.python.org/pypi/Flask-BabelEx/)
 * speaklater (https://pypi.python.org/pypi/speaklater/)
 * pytz (https://pypi.python.org/pypi/pytz/)
 * Babel (https://pypi.python.org/pypi/Babel/)
* Celery (https://pypi.python.org/pypi/celery/)
 * amqp (https://pypi.python.org/pypi/amqp/)
 * python-dateutil (https://pypi.python.org/pypi/python-dateutil/)
 * billiard (https://pypi.python.org/pypi/billiard/)
 * ordereddict (https://pypi.python.org/pypi/ordereddict/)
 * importlib (https://pypi.python.org/pypi/importlib/)
 * kombu (https://pypi.python.org/pypi/kombu/)
 * anyjson (https://pypi.python.org/pypi/anyjson/)
 * six (https://pypi.python.org/pypi/six/)
* supervisor
 * meld3 (https://pypi.python.org/pypi/meld3/)
* spyne (https://pypi.python.org/pypi/spyne/)
* SQLAlchemy (https://pypi.python.org/pypi/SQLAlchemy/)
* suds (https://pypi.python.org/pypi/suds/)
* simplejson (https://pypi.python.org/pypi/simplejson/)
* thrift (https://pypi.python.org/pypi/thrift/)

#### Перенос исходников ИС на сервер

Распаковать архив https://github.com/KorusConsulting/sobiralka/archive/master.zip в директорию проекта (/srv/my_project)


Настройка конфига ИС
-----------

Необходимо переопределить константы в файле settings_local.py в корне ИС
```
#Параметры подключения к БД
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'soap_user'
DB_PASSWORD = 'q1w2e3r4t5'
DB_NAME = 'soap_new'

#Системный пользователь, от которого будет запускаться вэб-сервер
SYSTEM_USER = 'is_user'

#Хост и порт, по которым будет доступе ИС
SOAP_SERVER_HOST = '127.0.0.1'
SOAP_SERVER_PORT = 9910

#Хост, по которому будет доступен административный интерфейс ИСа
SOAP_ADMIN_HOST = '127.0.0.1'

EPGU_SERVICE_URL = 'http://adapter-fer.rosminzdrav.ru/misAdapterService/ws/MisAdapterService?wsdl'
```

### Автоматическая установка ИС

```
fab alt_deploy
```
В процессе установки потребуется ввести логин/пароль администратора MySQL, из-под которого будет создан пользователь БД для ИС.

Настройка ИС
-----------
* Зайти в административный интерфейс:
http://IP_ADSRESS:8888/admin/
* Перейти в интерфейс управления Регионами:
http://IP_ADSRESS:8888/admin/regionsview/

Заполнить необходимую информацию о Регионах, с которыми будет взаимодействовать ИС
* Перейти в интерфейс управления списком ЛПУ:
http://IP_ADSRESS:8888/admin/lpuview/

Заполнить необходимую информацию о компонентах связи ЛПУ (КС), с которыми будет взаимодействовать ИС

**Импортирование данных в БД ИС из БД указанных КС**

```
fab update_db
```

Настроить и запустить supervisor для периодических задач
-----------
http://thomassileo.com/blog/2012/08/20/how-to-keep-celery-running-with-supervisor/
