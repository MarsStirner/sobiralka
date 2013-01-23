# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.abspath('..'))

from admin import app as application, admin, views
from admin.database import Session


admin.init_app(application)
admin.add_view(views.LPUAdmin(Session, name=u'Список ЛПУ'))
