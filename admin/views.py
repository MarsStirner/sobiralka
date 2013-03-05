# -*- coding: utf-8 -*-

from flask import request
from flask.ext.admin.contrib.sqlamodel import ModelView
from flask.ext.admin.base import expose, BaseView
from wtforms.fields import SelectField, BooleanField

from admin.models import LPU, Regions
from int_service.lib.dataworker import UpdateWorker


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


class UpdateAdmin(BaseView):
    @expose('/')
    def index(self):
        return self.render('update.html')

    @expose('/process/', methods=('POST',))
    def process(self):
        if request.form['do_update']:
            data_worker = UpdateWorker()
            data_worker.update_data()
            msg = data_worker.msg
        else:
            msg = [u'Ошибка обновления БД']
        return self.render('update_process.html', result_msg = msg)