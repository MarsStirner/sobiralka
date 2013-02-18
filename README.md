Интеграционный сервер (ИС)
=================

Интеграционный сервер обеспечивает взаимодействие между различными ТМИС.
Для установки ИС ознакомьтесь с системными требованиями и инструкцией, указанными ниже.

Системные требования
-----------

* Серверная ОС семейства Linux
* Python 2.7
* MySQL 5
* Web-Server Apache + mod_wsgi
* git
* zlib

Установка
-----------

Описанная ниже установка и настройка ПО производится из консоли Linux. Используется root-доступ.

**Update системы**

```
apt-get update
apt-get upgrade
```

**Установка виртуального окружения и инструмента работы с пакетами Python**

```
apt-get -y install mysql-client python python-dev python-setuptools
```

**Установка fabric для автоматического разворачивания проекта**

```
pip install fabric
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
