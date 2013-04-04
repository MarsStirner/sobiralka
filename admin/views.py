# -*- coding: utf-8 -*-

from flask import request
from flask.ext.admin.contrib.sqlamodel import ModelView
from flask.ext.admin.base import expose, BaseView
from wtforms.fields import SelectField, BooleanField

from admin.models import LPU, Regions, Speciality, EPGU_Speciality, EPGU_Service_Type
from int_service.lib.dataworker import UpdateWorker, EPGUWorker


class LPUAdmin(ModelView):
    column_exclude_list = ('LastUpdate', 'schedule', 'kladr', 'OGRN', 'type', 'keyEPGU', 'token')
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
                         keyEPGU=u'ID на ЕПГУ',
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


class SpecialityAdmin(ModelView):
    form_columns = ('name', 'epgu_speciality', 'epgu_service_type')
    column_list = ('name', 'epgu_speciality', 'epgu_service_type')
    column_labels = dict(name=u'Специальность',
                         epgu_speciality=u'Соответствие в ЕПГУ',
                         epgu_service_type=u'Услуга для выгрузки на ЕПГУ')
    column_sortable_list = ('name',)

    def __init__(self, session, **kwargs):
        super(SpecialityAdmin, self).__init__(Speciality, session, **kwargs)


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
        return self.render('update_process.html', result_msg=msg)


class SyncEPGUAdmin(BaseView):
    @expose('/')
    def index(self):
        return self.render('epgu_sync.html')

    @expose('/update_common_data/', methods=('POST',))
    def sync_common_data(self):
        if request.form['do_update']:
            data_worker = EPGUWorker()
            data_worker.sync_hospitals()
            data_worker.sync_reservation_types()
            data_worker.sync_payment_methods()
            msg = data_worker.msg
            del data_worker
        else:
            msg = [u'Ошибка обновления БД']
        return self.render('update_process.html', result_msg=msg)

    @expose('/update_specialitites/', methods=('POST',))
    def sync_specialitites(self):
        if request.form['do_update']:
            data_worker = EPGUWorker()
            data_worker.sync_specialities()
            msg = data_worker.msg
            del data_worker
        else:
            msg = [u'Ошибка обновления БД']
        return self.render('update_process.html', result_msg=msg)

    @expose('/update_locations/', methods=('POST',))
    def sync_locations(self):
        if request.form['do_update']:
            data_worker = EPGUWorker()
            data_worker.sync_locations()
            msg = data_worker.msg
            del data_worker
        else:
            msg = [u'Ошибка обновления БД']
        return self.render('update_process.html', result_msg=msg)

    @expose('/update_schedules/', methods=('POST',))
    def sync_schedules(self):
        if request.form['do_update']:
            data_worker = EPGUWorker()
            data_worker.sync_schedule()
            msg = data_worker.msg
            del data_worker
        else:
            msg = [u'Ошибка обновления БД']
        return self.render('update_process.html', result_msg=msg)