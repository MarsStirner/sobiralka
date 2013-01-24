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
apt-get -y install python python-dev python-setuptools
easy_install virtualenv pip
```

**Конфигурирование MySQL**

```
echo "CREATE DATABASE DATABASENAME;" | mysql -u root -p
echo "CREATE USER 'DATABASEUSER'@'localhost' IDENTIFIED BY 'PASSWORD';" | mysql -u root -p
echo "GRANT ALL PRIVILEGES ON DATABASENAME.* TO 'DATABASEUSER'@'localhost';" | mysql -u root -p
echo "FLUSH PRIVILEGES;" | mysql -u root -p
```

Из под root-пользователя БД рекомендуется создать пользователя БД с ограниченными правами, который будет использован в проекте для работы с БД.
DATABASENAME - название БД для ИС
DATABASEUSER - пользователь БД для ИС
PASSWORD - пароль пользователя БД для ИС

Подробнее про создание пользователей и раздачу прав можно почитать в оф. документации MySQL:

http://dev.mysql.com/doc/refman/5.1/en/create-user.html

http://dev.mysql.com/doc/refman/5.1/en/grant.html

Для работы с данными пользователю БД достаточно следующего набора привилегий:
SELECT, INSERT, UPDATE, DELETE, FILE, CREATE, ALTER, INDEX, DROP, CREATE TEMPORARY TABLES

**Подготовка директорий для размещения проекта**

Используем директорию /srv/ для обеспечения защищенной установки сайта. Вместо /srv можно использовать любую удобную директорию на сервере (например, /var/www/webapps). При этом, следуя инструкции, необходимо подразумевать, что вместо /srv необходимо указывать Вашу директорию.

В качестве имени проекта (my_project) можно использовать произвольное.
```
cd /srv/
mkdir -p my_project/app my_project/app/conf/apache
mkdir -p my_project/logs my_project/run/eggs
```

**Создаём и активируем виртульное окружение для проекта**

```
virtualenv my_project/venv
source my_project/venv/bin/activate
```

**Создаём системного пользователя**

Пользователь, из-под которого будет работать mod_wsgi процесс.
В качестве USERNAME используется произвольное имя.
```
useradd --system --no-create-home --home-dir /srv/my_project/ --user-group USERNAME
chsh -s /bin/bash USERNAME
```

**Клонирование github репозитория**

Перейти в корневую директорию проекта (в нашем примере: /srv/my_project) и выполнить команду:
```
git clone https://github.com/KorusConsulting/elreg.git
```
при этом необходимо наличие github аккаунта с правами доступа в корпоративный репозиторий


**Установка библиотек и приложений**

Устанавливаем ПО для разрешения зависимостей

* Для mysql-python:

```
apt-get build-dep python-mysqldb
```
* Для PIL (установка модулей и настройка путей к библиотекам):

```
apt-get install libjpeg8 libjpeg8-dev libfreetype6 libfreetype6-dev
ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib
ln -s /usr/lib/x86_64-linux-gnu/libfreetype.so /usr/lib
ln -s /usr/lib/x86_64-linux-gnu/libz.so /usr/lib
```

* Для работы SOAP-сервера

```
apt-get install libxml2-devel libxslt-devel
```

**Устанавливаем Flask и используемые модули**

```
pip install -r elreg/ElReg/requirements.txt
```

При получении сообщений об ошибках необходимо разрешить необходимые зависимости и повторно выполнить установку из requirements.txt. В конечном результате все пакеты должны установиться без уведомления об ошибках.


**Настройка Apache**

Создать конфиг сайта и отредактировать его любым текстовым редактором, в качестве DOMAIN использовать выбранное доменное имя сайта:
```
nano /etc/apache2/sites-available/DOMAIN
```

вставить следующее содержимое, подставив вместо USER и DOMAIN имя ранее созданного пользователя и выбранный домен:

```
<VirtualHost *:80>
ServerAdmin root@DOMAIN
ServerName DOMAIN

Alias /site_media/ /srv/my_project/elreg/ElReg/elreg_app/media/
Alias /static_admin/ /srv/my_project/venv/lib/python2.7/site-packages/django/contrib/admin/static/
Alias /static/ /srv/my_project/elreg/ElReg/elreg_app/static/
Alias /robots.txt /srv/my_project/app/webapp/site_media/robots.txt
Alias /favicon.ico /srv/my_project/elreg/ElReg/elreg_app/static/images/favicon.ico

CustomLog "|/usr/sbin/rotatelogs /srv/my_project/logs/access.log.%Y%m%d-%H%M%S 5M" combined
ErrorLog "|/usr/sbin/rotatelogs /srv/my_project/logs/error.log.%Y%m%d-%H%M%S 5M"
LogLevel warn

WSGIDaemonProcess DOMAIN user=USER group=USER processes=1 threads=15 maximum-requests=10000 python-path=/srv/my_project/venv/lib/python2.7/site-packages python-eggs=/srv/my_project/run/eggs
WSGIProcessGroup DOMAIN
WSGIScriptAlias / /srv/my_project/elreg/ElReg/wsgi.py

<Directory /srv/my_project/elreg/ElReg/elreg_app/media>
Order deny,allow
Allow from all
Options -Indexes FollowSymLinks
</Directory>

<Directory /srv/my_project/app/conf/apache>
Order deny,allow
Allow from all
</Directory>

</VirtualHost>
```

** Активировать конфигурацию:

DOMAIN - ранее выбранный домен
```
a2ensite DOMAIN
```

**Установить привилегии для директории проекта**

```
chown -R USERNAME:USERNAME /srv/my_project/
```

**Перезапустить апач**

```
service apache2 restart
```

**Настройка django**

Для первоначальной настройки django необходимо прописать параметры подключение к БД в файле /srv/my_project/elreg/ElReg/settings_local.py
Затем выполнить команду для создания таблиц в БД:
```
python elreg/ElReg/manage.py syncdb
python elreg/ElReg/manage.py migrate
```

В процессе будет предложено ввести логин/пароль администратора.

**Восстановление дампа БД**
```
python elreg/ElReg/manage.py loaddata elreg/ElReg/elreg.json
```

**Настройка сайта**
* Зайти в административный интерфейс:
http://DOMEN/admin/
* Ввести логин/пароль администратора
* Перейти в интерфес настроек сайта:
http://DOMEN/admin/settings/
* Заполнить необходимую информацию о текущем сайте, почтовом сервере, часовом поясе

-----------
**Замечания**

Может понадобиться прописать пути к виртуальному окружению в wsgi скрипте (в случае, если при открытии сайта в логах обнаружатся ошибки о недостающих библиотеках)
Для этого необходимо внести следующие строки в файл wsgi.py (до импорта from django.core.wsgi import get_wsgi_application):

```
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.abspath(os.path.join(root_path, 'venv/lib/python2.7/site-packages/')))
sys.path.insert(0, os.path.abspath(os.path.join(root_path, 'app')))
sys.path.insert(0, os.path.abspath(os.path.join(root_path, 'app', 'webapp')))
```

* Применение изменений, внесенных в файлы .py

Для того, чтобы избавиться от постоянно перезагрузки Apache после внесения изменений в файлы проекта, достаточно выполнить следующую команду:

```
touch /srv/my_project/elreg/ElReg/wsgi.py
```

Дополнительную информацию по настройке сервера можно получить по адресу:

http://www.lennu.net/2012/05/14/django-deployement-installation-to-ubuntu-12-dot-04-server/