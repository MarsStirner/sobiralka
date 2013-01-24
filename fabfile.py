#-*- coding: utf-8 -*-
import sys, os, getpass
from fabric.api import local, settings, abort, lcd
from fabric import operations

from settings import *

project_dir_path = os.path.abspath('..')
project_dir_name = os.path.basename(os.path.abspath('..'))
code_dir = os.path.basename(os.path.abspath('.'))

def prepare_virtual_env():
    #Установка виртуального окружения и инструмента работы с пакетами Python
    local('easy_install virtualenv pip')
    #Создаём и активируем виртульное окружение для проекта
    with lcd(project_dir_path):
        local('virtualenv .virtualenv')
        local('source .virtualenv/bin/activate')

def configure_db():
    #Создаём БД
    queries = []
    user = operations.prompt("Please specify MySQL admin user: ")
#    password = getpass.getpass("Please specify MySQL admin password: ")
    queries.append( "CREATE DATABASE IF NOT EXISTS %s;" % DB_NAME)
    #Создаём пользователя для работы с БД
    db_user_host = DB_HOST
    if db_user_host not in ('localhost', '127.0.0.1'):
        db_user_host = '%'
    if DB_USER != 'root':
#        queries.append("CREATE USER '%s'@'%s' IDENTIFIED BY '%s';" % (DB_USER, db_user_host, DB_PASSWORD))
        queries.append(
            '''GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, CREATE TEMPORARY TABLES, LOCK TABLES ON %s.* TO '%s'@'%s' IDENTIFIED BY '%s';''' %
            (DB_NAME, DB_USER, db_user_host, DB_PASSWORD)
        )
    #Выдаём пользователю привелегии на работу с БД
#    queries.append("GRANT ALL PRIVILEGES ON %s.* TO '%s'@'%s';" % (DB_NAME, DB_USER, db_user_host))
    queries.append("FLUSH PRIVILEGES;")
    local('echo "%s" | mysql -h %s -u %s -p' % (' '.join(queries), DB_HOST, user))

def prepare_directories():
    with lcd(project_dir_path):
        local('mkdir -p logs')
        local('mkdir -p run/eggs')

def create_system_user():
    #Создаём системного пользователя
    local('/usr/sbin/useradd --system --no-create-home --home-dir %s --user-group %s' % (project_dir_path, SYSTEM_USER))
    local('chsh -s /bin/bash %s' % SYSTEM_USER)
    local('chown -R %s:%s %s' % (SYSTEM_USER, SYSTEM_USER, project_dir_path))

def configure_webserver():
    #Создаём конфиги apache на основе имеющихся шаблонов и заданыых настроек
    with lcd(project_dir_path):
        is_config_file = open('%s/fabric_inc/int_server.config' % project_dir_path, 'r')
        is_config = _parse_config(is_config_file.read())
        is_config_file.close(is_config_file)
        apache_is_config_file = open('/etc/httpd2/conf/sites-available/%s' % project_dir_name, 'w')
        apache_is_config_file.write(is_config)
        apache_is_config_file.close()

        admin_is_config_file = open('%sfabric_inc/admin_int_server.config' % project_dir_path, 'r')
        admin_is_config = _parse_config(admin_is_config_file.read())
        admin_is_config_file.close(admin_is_config_file)
        apache_admin_is_config_file = open('/etc/httpd2/conf/sites-available/admin_%s' % project_dir_name, 'w')
        apache_admin_is_config_file.write(admin_is_config)
        apache_admin_is_config_file.close()

def _parse_config(s):
    #Заменяем в шаблонах конфигов апача метки переменных на значения, заданные в settings
    edits = [('%SOAP_SERVER_HOST%', SOAP_SERVER_HOST),
             ('%PROJECT_ROOT%', project_dir_path),
             ('%PROJECT_NAME%', project_dir_name),
             ('%SYSTEM_USER%', SYSTEM_USER),
             ('%SOAP_ADMIN_HOST%', SOAP_ADMIN_HOST)]
    for search, replace in edits:
        s = s.replace(search, replace)
    return s

def activate_web_config():
    #Активируем конфигурации и перезапускаем apache
    local('a2ensite %s', project_dir_name)
    local('a2ensite admin_%s', project_dir_name)
    local('service httpd2 restart')

def install_requirements():
    #Устанавливаем необходимые модули python
    local('apt-get install python-mysqldb python-module-mysqldb')
    with lcd(project_dir_path):
        local('pip install -r requirements.txt')

def restore_database():
    #Создаём таблицы в БД на основе модели
    with lcd(project_dir_path):
        local('python admin/update.py')

def deploy():
    prepare_virtual_env()
    configure_db()
    prepare_directories()
    create_system_user()
    configure_webserver()
    activate_web_config()
    restore_database()