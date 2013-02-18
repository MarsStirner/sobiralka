# -*- coding: utf-8 -*-

from flask.ext.admin.contrib.sqlamodel import ModelView
from wtforms.fields import SelectField, BooleanField

from admin.models import LPU, Regions


class LPUAdmin(ModelView):
    form_overrides = dict(protocol=SelectField)
    form_args = dict(
        protocol=dict(
            choices=[('korus20', 'korus20'), ('korus30', 'korus30'), ('intramed', 'intramed')]
        ))

    def __init__(self, session, **kwargs):
        super(LPUAdmin, self).__init__(LPU, session, **kwargs)


class RegionsAdmin(ModelView):
    form_overrides = dict(is_active=BooleanField)

    def __init__(self, session, **kwargs):
        super(RegionsAdmin, self).__init__(Regions, session, **kwargs)