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

* C-compiler (gcc) ```apt-get install gcc4.5``` (установить подходящую версию)
 * binutils
 * cpp4.5
 * gcc-common
 * glibc
 * glibc-devel
 * glibc-kernheaders
 * glibc-timezones
 * kernel-headers-common
 * libmpc
 * libmprf
 * tzdata
* MySQL 5 (MySQL-server, MySQL-client) ```apt-get install MySQL-server``` ```apt-get install MySQL-client```
* python-module-MySQLdb ```apt-get install python-module-MySQLdb```
* libxml2-devel ```apt-get install libxml2-devel```
* libxslt-devel ```apt-get install libxslt-devel```
 * libxslt
* libmysqlclient-devel ```apt-get install libmysqlclient-devel```

**Пакеты для установке из Интернета**

* git (для случая, когда проект скачивается по интернету из репозитория) ```apt-get install git```
* python-module-setuptools (для случая, когда модули python устанавливаются из Интернета) ```apt-get install python-module-setuptools```
 * libinfo-devel
 * libncurses
 * libncurses-devel
 * python-dev

**Во вложенных пунктах указаны зависимости, которые потребуется разрешить**


Установка ИС
-----------

Описанная ниже установка и настройка ПО производится из консоли Linux. Используется root-доступ.


### Установка и настройка виртуального окружения, библиотек Python

```
apt-get install python-module-virtualenv
```

**Перенос исходников ИС на сервер**

Используем директорию /srv/ для обеспечения защищенной установки ИС. Вместо /srv можно использовать любую удобную директорию на сервере (например, /var/www/webapps).

При этом, следуя инструкции, необходимо подразумевать, что вместо /srv необходимо указывать Вашу директорию.

В качестве имени проекта (my_project) можно использовать произвольное.

```
cd /srv/my_project
git clone https://github.com/KorusConsulting/sobiralka.git
```
при этом необходимо наличие github аккаунта с правами доступа в корпоративный репозиторий

**Если доступа к репозиторию нет, но есть архив с исходниками проекта - достаточно распаковать его в отведенную директорию.**


**Установка fabric для автоматического разворачивания проекта**

```
easy_install fabric
```


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

**Автоматическая установка ИС и зависимостей**

```
fab deploy
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
