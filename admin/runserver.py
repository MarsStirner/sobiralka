#!/usr/bin/env python
# -*- coding: utf-8 -*-
from admin import app, admin
from flask.ext.admin.contrib.sqlamodel import ModelView
from admin.models import LPU
from admin.database import Session

import views

admin.init_app(app)
admin.add_view(views.LPUAdmin(Session, name=u'Список ЛПУ'))

if __name__ == "__main__":
    app.run(debug=True)