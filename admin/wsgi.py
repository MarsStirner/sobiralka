# -*- coding: utf-8 -*-
import sys, os
from admin import app as application, admin
from admin.database import Session
import views

sys.path.insert(0, os.path.dirname(__file__))

admin.init_app(application)
admin.add_view(views.LPUAdmin(Session, name=u'Список ЛПУ'))
