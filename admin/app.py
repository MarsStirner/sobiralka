# -*- coding: utf-8 -*-
from flask import Flask
from flask.ext.admin import Admin
from settings import FLASK_SECRET_KEY
from admin.database import Session
from admin import views

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
admin = Admin(app)
#admin.init_app(app)
admin.locale_selector(lambda: 'ru')

admin.add_view(views.RegionsAdmin(Session, name=u'Список Регионов'))
admin.add_view(views.LPUAdmin(Session, name=u'Список ЛПУ'))


@app.teardown_request
def shutdown_session(exception=None):
    Session.remove()