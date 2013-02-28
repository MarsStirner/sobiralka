# -*- coding: utf-8 -*-

from flask.ext.admin.contrib.sqlamodel import ModelView
from wtforms.fields import SelectField, BooleanField

from admin.models import LPU, Regions


class LPUAdmin(ModelView):
    column_exclude_list = ('LastUpdate', 'schedule', 'kladr', 'OGRN', 'type', 'token')
    form_excluded_columns = ('LastUpdate', 'schedule', )
    column_labels = dict(name=u'Наименование',
                         address=u'Адрес',
                         key=u'Инфис-код',
                         kladr=u'КЛАДР',
                         OGRN=u'ОГРН',
                         OKATO=u'ОКАТО',
                         type=u'Тип ЛПУ',
                         phone=u'Телефон',
                         protocol=u'Протокол',
                         token=u'Токен')
    form_overrides = dict(protocol=SelectField)
    form_args = dict(
        protocol=dict(
            choices=[('korus20', 'korus20'), ('korus30', 'korus30'), ('intramed', 'intramed')]
        ))

    def __init__(self, session, **kwargs):
        super(LPUAdmin, self).__init__(LPU, session, **kwargs)


class RegionsAdmin(ModelView):
    form_overrides = dict(is_active=BooleanField)
    column_labels = dict(name=u'Название региона', code=u'ОКАТО', is_active=u'Активен')
    column_sortable_list = ('name',)

    def __init__(self, session, **kwargs):
        super(RegionsAdmin, self).__init__(Regions, session, **kwargs)
