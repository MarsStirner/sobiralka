# -*- coding: utf-8 -*-
from flask import Flask, request, session
from flask.ext.admin import Admin
from flask.ext.babelex import Babel
from settings import FLASK_SECRET_KEY
from admin.database import Session
from admin import views

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
admin = Admin(app, name=u'Управление ИС')

# Initialize babel
babel = Babel(app)

@babel.localeselector
def get_locale():
    override = request.args.get('lang')

    if override:
        session['lang'] = override

    return session.get('lang', 'ru')

admin.add_view(views.RegionsAdmin(Session, name=u'Список Регионов'))
admin.add_view(views.LPUAdmin(Session, name=u'Список ЛПУ'))
admin.add_view(views.SpecialityAdmin(Session, name=u'Специальности'))
admin.add_view(views.UpdateAdmin(name=u'Обновление БД', category=u'Обновление данных'))
admin.add_view(views.SyncEPGUAdmin(name=u'Синхронизация с ЕПГУ', category=u'Обновление данных'))


@app.teardown_request
def shutdown_session(exception=None):
    Session.remove()