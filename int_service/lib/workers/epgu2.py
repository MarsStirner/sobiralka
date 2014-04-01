# -*- coding: utf-8 -*-
import exceptions
import datetime
import time
import sqlalchemy

try:
    import json
except ImportError:
    import simplejson as json

import hl7

from sqlalchemy import or_, and_, func, not_
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm.scoping import ScopedSession
from admin.models import LPU, Enqueue, Personal, Speciality
from admin.models import Personal_Specialities, EPGU2_Speciality, EPGU2_Post, EPGU2_Service, Personal_KeyEPGU
from admin.models import EPGU2_Payment_Method, EPGU_Reservation_Type, Tickets
from ..service_clients import Clients, CouponStatus

from admin.database import Session, Session2, init_task_session, shutdown_session
from ..utils import logger
from ..dataworker import DataWorker
from ..is_exceptions import EPGUError

logger_tags = dict(tags=['dataworker', 'IS'])


class EPGUWorker(object):
    """Класс взаимодействия с ЕПГУ"""

    class Struct:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def __init__(self, session=None, lpu_id=None):
        self.msg = []
        self.time_table_period = 90  # TODO: вынести в настройки
        self.schedule_weeks_period = 3  # TODO: вынести в настройки
        self.default_phone = '+79011111111'
        if session is not None and isinstance(session, sqlalchemy.orm.Session):
            self.session = session
        else:
            self.session = Session2()

        self.proxy_client = Clients.provider('epgu2', auth_token=self.__get_token(lpu_id))

    def __del__(self):
        shutdown_session()
        logger.debug(u'\n'.join(self.msg), extra=dict(tags=['epgu2_worker', 'IS']))

    def __log(self, msg):
        if msg:
            if isinstance(msg, list):
                for m in msg:
                    self.msg.append(m)
                self.__log(u'-----')
            else:
                self.msg.append(msg)

    def __get_token(self, lpu_id=None):
        if lpu_id:
            lpu_token = self.session.query(LPU.epgu2_token).filter(and_(LPU.id == lpu_id)).first()
        else:
            lpu_token = self.session.query(LPU.epgu2_token).filter(and_(LPU.epgu2_token != '',
                                                                        LPU.epgu2_token != None)).first()
        if lpu_token:
            return lpu_token.epgu2_token
        return None

    def __failed_update(self, error=""):
        self.session.rollback()
        # shutdown_session()
        if error:
            self.__log(u'Ошибка синхронизации: %s' % error)
            self.__log(u'----------------------------')
        return False

    def __success_update(self):
        self.session.commit()
        # shutdown_session()
        return True

    def sync_specialities(self):
        lpu_dw = DataWorker.provider('lpu')
        lpu_list = lpu_dw.get_list()
        if lpu_list:
            for lpu in lpu_list:
                if not lpu.token:
                    continue
                self.sync_posts()
                self.proxy_client.set_auth_token(lpu.epgu2_token)
                try:
                    specialities = self.proxy_client.GetSpecs()
                except EPGUError, e:
                    self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
                else:
                    if specialities:
                        epgu_specialities = self.__update_epgu_specialities(specialities=specialities)
                        self.__update_services(specialities=epgu_specialities)
                    self.__log(u'Синхронизированы специальности, должности и услуги по ЛПУ %s' % lpu.name)
                    self.__log(u'----------------------------')

    def sync_posts(self, epgu2_token=None):
        if epgu2_token:
            self.proxy_client.set_auth_token(epgu2_token)
        try:
            posts = self.proxy_client.GetPosts()
        except EPGUError, e:
            self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
        else:
            if posts:
                epgu_posts = self.__update_epgu_posts(posts=posts)

    def __update_epgu_posts(self, posts):
        result = []
        for post in posts:
            db_post = self.session.query(EPGU2_Post).get(post['post']['id'])
            if not db_post:
                epgu_post = EPGU2_Post(**post['post'])
                self.session.add(epgu_post)
                result.append(epgu_post.id)
                self.session.commit()
            else:
                result.append(db_post.id)
        return result

    def __update_epgu_specialities(self, specialities):
        result = []
        for speciality in specialities:
            db_speciality = self.session.query(EPGU2_Speciality).get(speciality['spec']['id'])
            if not db_speciality:
                epgu_speciality = EPGU2_Speciality(**speciality['spec'])
                self.session.add(epgu_speciality)
                result.append(epgu_speciality.id)
                self.session.commit()
            elif not db_speciality.code:
                db_speciality.code = speciality['spec']['code']
                result.append(db_speciality.id)
                self.session.commit()
            else:
                result.append(db_speciality.id)
        return result

    def __update_services(self, specialities):
        for speciality_id in specialities:
            try:
                services = self.proxy_client.GetServices(spec_id=speciality_id)
            except EPGUError, e:
                self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
            else:
                if services:
                    if not isinstance(services, list):
                        services = [services]
                    for service in services:
                        exists = (self.session.query(EPGU2_Service).
                                  filter(EPGU2_Service.id == service['service']['id']).count())
                        if not exists:
                            self.session.add(EPGU2_Service(id=service['service']['id'],
                                                           name=service['service']['name'],
                                                           code=service['service']['code'],
                                                           spec_recid=service['service']['spec_recid'],
                                                           speciality_id=speciality_id))
                            self.session.commit()

    def sync_payment_methods(self):
        auth_token = self.__get_token()
        if auth_token:
            epgu_result = self.proxy_client.GetPayments()
            if epgu_result:
                for _method in epgu_result:
                    if not (self.session.query(EPGU2_Payment_Method).
                            filter(EPGU2_Payment_Method.code == _method['payment']['code']).
                            count()):
                        self.session.add(EPGU2_Payment_Method(name=_method['payment']['name'],
                                                              code=_method['payment']['code']))
                        self.session.commit()
                self.__log(u'Методы оплаты синхронизированы')
                self.__log(u'----------------------------')
            else:
                self.__log(getattr(epgu_result, 'error', None))

    def sync_reservation_types(self):
        pass

    def __get_doctor_by_location(self, doctor_epgu_id, lpu_id):
        doctor = self.session.query(Personal).filter(Personal_KeyEPGU.epgu2_id==doctor_epgu_id, Personal.lpuId == lpu_id).first()
        return doctor

    def __update_doctor(self, doctor, data):
        # Заново выбираем, т.к. не работает update commit с текущим пользователем (видимо, Session его забывает)
        doctor = self.session.query(Personal).get(doctor.id)
        for k, v in data.items():
            if k == 'keyEPGU':
                doctor.key_epgu.keyEPGU = v
            elif k == 'epgu2_resource_id':
                doctor.key_epgu.epgu2_resource_id = v
            elif k == 'epgu2_id':
                doctor.key_epgu.epgu2_id = v
            elif hasattr(doctor, k):
                setattr(doctor, k, v)
        self.session.commit()

    def __delete_location_epgu(self, resource_id):
        self.proxy_client.DeleteResource(resource_id)

    def __get_location_data(self, locations):
        result = []
        try:
            for location in locations.location:
                result.append(
                    dict(
                        prefix=location.prefix,
                        keyEPGU=location.id,
                        epgu_speciality=getattr(location, 'medical-specialization').id
                    ))
        except AttributeError, e:
            print e
            logger.error(e, extra=logger_tags)
        return result

    def __get_all_locations(self):
        try:
            result = self.proxy_client.GetResources(dict(params=dict()))
        except EPGUError, e:
            self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
        else:
            return result
        return []

    def __get_nearest_monday(self):
        today = datetime.date.today()
        if today.isoweekday() == 1:
            nearest_monday = today
        else:
            nearest_monday = today + datetime.timedelta(days=(7 - today.isoweekday() + 1))
        return nearest_monday

    def __get_min_quantum_time(self, timeslots):
        if timeslots:
            times = list()  # TODO: set() is better
            for timeslot in timeslots:
                times.append((timeslot['finish'] - timeslot['start']).seconds / 60)
            return min(times)
        return None

    def __get_quantum_time(self, doctor, date=None):
        enqueue_dw = DataWorker.provider('enqueue', self.session)
        if date is None:
            date = self.__get_nearest_monday()
        params = {
            'hospitalUid': '%s/%s' % (doctor.lpuId, doctor.orgId),
            'doctorUid': doctor.doctor_id,
            'startDate': date,
            'endDate': date + datetime.timedelta(weeks=self.schedule_weeks_period)
        }
        result = enqueue_dw.get_info(**params)
        if result['timeslots']:
            return self.__get_min_quantum_time(result['timeslots'])
        return None

    def __get_service_types(self, doctor, epgu_speciality_id):
        if not doctor.speciality[0].epgu2_service:
            raise exceptions.ValueError
        return [doctor.speciality[0].epgu2_service]
        # return (self.session.query(EPGU_Service_Type).
        #         filter(EPGU_Service_Type.epgu_speciality_id == epgu_speciality_id).
        #         all())

    def __post_location_epgu(self, doctor):
        if not hasattr(doctor, 'speciality') or not isinstance(doctor.speciality, list):
            self.__log(
                u'Не найдена специальность у врача %s %s %s (id=%s)' %
                (doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        epgu2_speciality = doctor.speciality[0].epgu2_speciality
        if not epgu2_speciality:
            self.__log(
                u'Нет соответствия специальности %s на ЕПГУ для врача %s %s %s (id=%s)' %
                (doctor.speciality[0].name, doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        try:
            epgu2_service = self.__get_service_types(doctor, epgu2_speciality.id)
        except AttributeError, e:
            print e
            logger.error(e, extra=logger_tags)
            self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
            return None
        except exceptions.ValueError, e:
            print e
            logger.error(e, extra=logger_tags)
            self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
            return None

        params = dict()
        # payment_method = self.session.query(EPGU2_Payment_Method).filter(EPGU2_Payment_Method.default == True).one()
        payment_method = self.session.query(EPGU2_Payment_Method).filter(EPGU2_Payment_Method.code == 'oms').one()

        quantum_time = self.__get_quantum_time(doctor)
        if not quantum_time:
            self.__log(u'Не заведено расписание для %s %s %s (id=%s)' %
                       (doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        params['spec_id'] = epgu2_speciality.id
        params['norms'] = []
        for service in epgu2_service:
            params['norms'].append(dict(norm=dict(service_id=service.id)))
        params['doctor_id'] = doctor.key_epgu.epgu2_id
        params['span'] = self.time_table_period
        params['reserve'] = 15
        params['payment'] = payment_method.code
        params['is_automatic'] = True
        params['is_autoactivated'] = True
        params['resource_type'] = 'single'
        params['is_dynamic'] = False
        params['is_quoted'] = False
        params['has_waits'] = False
        params['quantum'] = quantum_time
        params['source_codes'] = list()
        params['source_codes'].append(dict(source_code='reg'))
        params['source_codes'].append(dict(source_code='epgu'))
        params['source_codes'].append(dict(source_code='kc'))
        params['source_codes'].append(dict(source_code='ter'))
        params['source_codes'].append(dict(source_code='mis'))

        try:
            epgu2_resource = self.proxy_client.CreateResource(params)
        except EPGUError, e:
            self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
        else:
            if epgu2_resource:
                return epgu2_resource['id']
        return None

    def __put_edit_location_epgu(self, doctor, resource_id):
        if not hasattr(doctor, 'speciality') or not isinstance(doctor.speciality, list):
            self.__log(
                u'Не найдена специальность у врача %s %s %s (id=%s)' %
                (doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        epgu2_speciality = doctor.speciality[0].epgu2_speciality
        if not epgu2_speciality:
            self.__log(
                u'Нет соответствия специальности %s на ЕПГУ для врача %s %s %s (id=%s)' %
                (doctor.speciality[0].name, doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        try:
            epgu2_service = self.__get_service_types(doctor, epgu2_speciality.id)
        except AttributeError, e:
            print e
            logger.error(e, extra=logger_tags)
            self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
            return None
        except exceptions.ValueError, e:
            print e
            logger.error(e, extra=logger_tags)
            self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
            return None

        params = dict()
        # payment_method = self.session.query(EPGU2_Payment_Method).filter(EPGU2_Payment_Method.default == True).one()
        payment_method = self.session.query(EPGU2_Payment_Method).filter(EPGU2_Payment_Method.code == 'oms').one()

        quantum_time = self.__get_quantum_time(doctor)
        if not quantum_time:
            self.__log(u'Не заведено расписание для %s %s %s (id=%s)' %
                       (doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        params['spec_id'] = epgu2_speciality.id
        params['norms'] = []
        for service in epgu2_service:
            params['norms'].append(dict(norm=dict(service_id=service.id)))
        params['doctor_id'] = doctor.key_epgu.epgu2_id
        params['span'] = self.time_table_period
        params['reserve'] = 15
        params['payment'] = payment_method.code
        params['is_automatic'] = True
        params['is_autoactivated'] = True
        params['resource_type'] = 'single'
        params['is_dynamic'] = False
        params['is_quoted'] = False
        params['has_waits'] = False
        params['quantum'] = quantum_time
        params['source_codes'] = list()
        params['source_codes'].append(dict(source_code='reg'))
        params['source_codes'].append(dict(source_code='epgu'))
        params['source_codes'].append(dict(source_code='kc'))
        params['source_codes'].append(dict(source_code='ter'))
        params['source_codes'].append(dict(source_code='mis'))

        try:
            epgu2_resource = self.proxy_client.UpdateResource(resource_id, params)
        except EPGUError, e:
            self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
        else:
            if epgu2_resource:
                return epgu2_resource['id']
        return None

    def sync_locations(self):
        lpu_dw = DataWorker.provider('lpu')
        lpu_list = lpu_dw.get_list()
        if lpu_list:
            for lpu in lpu_list:
                if not lpu.epgu2_token:
                    continue

                self.proxy_client.set_auth_token(lpu.epgu2_token)
                epgu2_doctors = []
                try:
                    epgu2_doctors = self.proxy_client.GetDoctors()
                except EPGUError, e:
                    self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
                    print e

                self.__log(u'Синхронизация очередей для %s' % lpu.name)
                resources = self.__get_all_locations()
                _exists_locations_id = []
                _synced_doctor = []
                if resources:
                    for resource in resources:
                        doctor_epgu2_id = resource['resource']['doctor_id']
                        doctor = self.__get_doctor_by_location(doctor_epgu2_id, lpu.id)
                        if doctor and doctor.key_epgu and str(doctor.key_epgu.epgu2_resource_id) == resource['resource']['id']:
                            self.__log(u'Для %s %s %s epgu2_resource_id (%s) в ИС и на ЕПГУ совпадают' %
                                       (doctor.LastName, doctor.FirstName, doctor.PatrName, resource['resource']['id']))
                            _synced_doctor.append(doctor.id)
                            result = self.__put_edit_location_epgu(doctor, resource['resource']['id'])
                            if result:
                                self.__log(u'Очередь обновлена (%s)' % resource['resource']['id'])
                        elif doctor and (not doctor.key_epgu or str(doctor.key_epgu.epgu2_resource_id) != resource['resource']['id']):
                            self.__update_doctor(doctor, dict(epgu2_resource_id=resource['resource']['id']))
                            self.__log(u'Для %s %s %s получен epgu2_resource_id (%s)' %
                                       (doctor.LastName, doctor.FirstName, doctor.PatrName, resource['resource']['id']))
                            _synced_doctor.append(doctor.id)
                            result = self.__put_edit_location_epgu(doctor, resource['resource']['id'])
                            if result:
                                self.__log(u'Очередь обновлена (%s)' % resource['resource']['id'])
                        elif not doctor:
                            self.__delete_location_epgu(resource['resource']['id'])
                            self.__log(u'epgu2_resource_id не найден в БД ИС, на ЕПГУ удалена очередь (%s)' %
                                       (resource['resource']['id'],))

                add_epgu_doctors = (
                    self.session.query(Personal).
                    # options(joinedload(Personal.speciality)).
                    filter(Personal.lpuId == lpu.id).
                    filter(
                        or_(
                            Personal.key_epgu.has(Personal_KeyEPGU.epgu2_id == None),
                            not_(Personal.id.in_(_synced_doctor)))).
                    # filter(
                    #     or_(
                    #         Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU == None),
                    #         not_(Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU.in_(_exists_locations_id))))).
                    all())
                if add_epgu_doctors:
                    for doctor in add_epgu_doctors:
                        doctor = self.__find_doctor(doctor, epgu2_doctors)
                        if not doctor.key_epgu.epgu2_id:
                            doctor = self.__add_doctor(doctor)
                        location_id = self.__post_location_epgu(doctor)
                        if location_id:
                            message = (u'Для %s %s %s отправлена очередь, получен epgu2_resource_id (%s)' %
                                       (doctor.LastName, doctor.FirstName, doctor.PatrName, location_id))
                            self.__update_doctor(doctor, dict(epgu2_resource_id=location_id))
                            self.__log(message)
                self.__log(u'----------------------------')

    def __parse_snils(self, snils):
        return snils.replace('-', '').replace(' ', '')

    def __find_doctor(self, doctor, epgu_doctors):
        for epgu_doctor in epgu_doctors:
            if epgu_doctor and doctor.snils == self.__parse_snils(epgu_doctor['doctor']['snils']):
                self.__update_doctor(doctor, dict(epgu2_id=epgu_doctor['doctor']['id']))
                break
        return doctor

    def __add_doctor(self, doctor):
        params = dict(snils=doctor.snils, surname=doctor.LastName, name=doctor.FirstName, patronymic=doctor.PatrName)
        if doctor.speciality:
            specs = list()
            for speciality in doctor.speciality:
                if speciality.epgu2_service_id:
                    specs.append(dict(spec_id=speciality.epgu2_service_id))
            params.update(dict(spec_ids=specs))
        if doctor.post:
            posts = list()
            for post in doctor.post:
                posts.append(dict(post_id=post.epgu2_post_id))
            params.update(dict(post_ids=posts))
        try:
            result = self.proxy_client.CreateDoctor(params)
        except EPGUError, e:
            self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
        else:
            if result['id']:
                doctor.key_epgu.epgu2_id = result['id']
                self.session.commit()
        return doctor

    def __link_activate_schedule(self, hospital, location_id, rules):
        print (hospital, location_id, rules)
        epgu_result = self.proxy_client.PutLocationSchedule(
            hospital,
            location_id,
            rules)
        applied_schedule = getattr(epgu_result, 'applied-schedule', None)
        print applied_schedule
        if applied_schedule:
            applied_rules = getattr(applied_schedule, 'applied-rules', None)
            if applied_rules:
                applied_rule = getattr(applied_rules, 'applied-rule')
                if isinstance(applied_rule, list):
                    for _applied_rule in applied_rule:
                        self.__log(
                            u'Очереди (%s) назначено расписание с %s по %s (%s)' %
                            (getattr(applied_schedule, 'location-id', ''),
                             getattr(_applied_rule, 'start-date'),
                             getattr(_applied_rule, 'end-date'),
                             getattr(_applied_rule, 'rule-id')))
                else:
                    if applied_rule:
                        self.__log(
                            u'Очереди (%s) назначено расписание с %s по %s (%s)' %
                            (getattr(applied_schedule, 'location-id', ''),
                             getattr(applied_rule, 'start-date'),
                             getattr(applied_rule, 'end-date'),
                             getattr(applied_rule, 'rule-id')))

            # TODO: На Celery с задержкой
            time.sleep(3)
            epgu_result = self.proxy_client.PutActivateLocation(hospital, location_id)
            location = getattr(epgu_result, 'location', None)
            if location:
                self.__log(u'Очередь %s (%s) активирована' % (location.prefix, location.id))
            else:
                self.__log(getattr(epgu_result, 'error', None))
        else:
            self.__log(getattr(epgu_result, 'error', None))

    def __appoint_patients(self, hospital, doctor, patient_slots):
        for patient_slot in patient_slots:
            try:
                service_type = doctor.speciality[0].epgu_service_type
                service_type_keyEPGU = service_type.keyEPGU
            except AttributeError, e:
                print e
                self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
                continue
            fio_list = patient_slot['patient']['fio'].split()
            patient = dict(firstName=fio_list[1], lastName=fio_list[0], id=patient_slot['patient']['id'])
            try:
                patronymic = fio_list[2]
            except IndexError, e:
                print e
                patient['patronymic'] = u''
            else:
                patient['patronymic'] = patronymic

            key_epgu = self.session.query(Personal_KeyEPGU).filter(
                Personal_KeyEPGU.lpuId == doctor.lpuId,
                Personal_KeyEPGU.orgId == doctor.orgId,
                Personal_KeyEPGU.doctor_id == doctor.doctor_id
            ).one()
            self.epgu_appoint_patient(
                hospital=hospital,
                doctor=dict(location_id=key_epgu.keyEPGU, epgu_service_type=service_type_keyEPGU),
                patient=patient,
                timeslot=patient_slot['date_time']
            )

    def epgu_appoint_patient(self, hospital, doctor, patient, timeslot):
        slot_unique_key = None
        epgu_result = self.proxy_client.CreateSlot(
            hospital=hospital,
            doctor_id=doctor['location_id'],
            service_type_id=doctor['epgu_service_type'],
            date=dict(
                date=timeslot.date().strftime('%Y-%m-%d'), start_time=timeslot.time().strftime('%H:%M')
            )
        )
        slot = getattr(epgu_result, 'slot', None)
        if slot:
            patient = dict(name=patient['firstName'],
                           surname=patient['lastName'],
                           patronymic=patient['patronymic'],
                           phone=self.default_phone,
                           id=patient['id'])
            epgu_result = self.proxy_client.PutSlot(hospital, patient, getattr(slot, 'unique-key'))
            slot = getattr(epgu_result, 'slot', None)
            if slot:
                slot_unique_key = getattr(slot, 'unique-key')
                self.__log(u'На ЕПГУ добавлен талончик для %s %s %s (%s %s), ID очереди=%s, получен keyEPGU (%s)'
                           % (patient['surname'],
                              patient['name'],
                              patient['patronymic'],
                              timeslot.date().strftime('%d.%m.%Y'),
                              timeslot.time().strftime('%H:%M'),
                              doctor['location_id'],
                              slot_unique_key))
            else:
                self.__log(getattr(epgu_result, 'error', None))
                #print getattr(epgu_result, 'error', '').encode('utf-8')
        else:
            self.__log(getattr(epgu_result, 'error', None))
            #print getattr(epgu_result, 'error', '').encode('utf-8')
        return slot_unique_key

    def epgu_delete_slot(self, hospital, slot_id):
        epgu_result = self.proxy_client.DeleteSlot(hospital, slot_id)
        _hash = getattr(epgu_result, '_hash', None)
        if not _hash:
            self.__log(getattr(epgu_result, 'error', None))
        return _hash

    def __post_rules(self, epgu2_resource_id, start_date, week_number, doctor, days):
        rule_start = start_date + datetime.timedelta(weeks=(week_number - 1))
        rule_end = rule_start + datetime.timedelta(days=6)

        params = dict()
        params['resource_id'] = epgu2_resource_id
        params['name'] = u'%s %s.%s. (%s-%s)' % (doctor.LastName,
                                                 doctor.FirstName[0:1],
                                                 doctor.PatrName[0:1],
                                                 rule_start.strftime('%d.%m.%Y'),
                                                 rule_end.strftime('%d.%m.%Y'))
        params['from'] = rule_start.strftime('%Y-%m-%d')
        params['till'] = rule_end.strftime('%Y-%m-%d')
        params['consider'] = 'all'
        params['is_exception'] = False
        params['atoms'] = list()
        for day in days:
            weekday = day['date'].weekday()
            for atom in day['interval']:
                params['atoms'].append({'atom': {
                    'weekday': weekday,
                    'even': True,
                    'odd': True,
                    'from': atom['start'],
                    'till': atom['end'],
                    'source_codes': [
                        {'source_code': 'reg'},
                        {'source_code': 'epgu'},
                        {'source_code': 'kc'},
                        {'source_code': 'ter'},
                        {'source_code': 'mis'}]
                }})

        try:
            result = self.proxy_client.CreateRule(dict(rule=params))
        except EPGUError, e:
            self.__log(u'Error: {0} (code: {1})'.format(e.message, e.code))
        else:
            if result:
                self.__log(
                    u'На ЕПГУ отправлено расписание для %s %s %s (%s-%s)' %
                    (doctor.LastName,
                     doctor.FirstName,
                     doctor.PatrName,
                     rule_start.strftime('%d.%m.%Y'),
                     rule_end.strftime('%d.%m.%Y')))
            return result
        return None

    def sync_schedule(self):
        lpu_dw = DataWorker.provider('lpu')
        lpu_list = lpu_dw.get_list()
        #TODO: распараллелить по ЛПУ? и вызывать из Celery после апдейта location
        hospital = list()
        if lpu_list:
            for lpu in lpu_list:
                if not lpu.epgu2_token:
                    continue
                self.proxy_client.set_auth_token(lpu.epgu2_token)

                today = datetime.datetime.today().date()
                # TODO: get nearest monday for start_date?
                start_date = today - datetime.timedelta(days=(today.isoweekday() - 1))  # + datetime.timedelta(weeks=1)
                end_date = start_date + datetime.timedelta(weeks=self.schedule_weeks_period)
                enqueue_dw = DataWorker.provider('enqueue', Session2())
                epgu_doctors = self.session.query(Personal).filter(Personal.lpuId == lpu.id,
                                                                   Personal.key_epgu.has(
                                                                       Personal_KeyEPGU.epgu2_resource_id != None
                                                                   )).all()
                for doctor in epgu_doctors:
                    params = {
                        'hospitalUid': '%s/%s' % (doctor.lpuId, doctor.orgId),
                        'doctorUid': doctor.doctor_id,
                        'startDate': start_date,
                        'endDate': end_date,
                    }
                    resource_id = doctor.key_epgu.epgu2_resource_id

                    schedule = enqueue_dw.get_info(**params)
                    if schedule:
                        doctor_rules = []
                        busy_by_patients = []
                        days = []
                        interval = []
                        week_number = 1
                        previous_day = None
                        for timeslot in schedule['timeslots']:
                            #TODO: понять, как будет с Интрамедом
                            if timeslot['status'] == 'disabled':
                                continue

                            if previous_day is not None and previous_day.date() != timeslot['start'].date():
                                days.append(dict(date=previous_day, interval=interval))
                                interval = []

                            interval.append(dict(start=timeslot['start'].time().strftime('%H:%M'),
                                                 end=timeslot['finish'].time().strftime('%H:%M')))

                            previous_day = timeslot['start']

                            if timeslot['start'].date() >= (start_date + datetime.timedelta(weeks=week_number)):
                                if days:
                                    epgu_rule = self.__post_rules(resource_id, start_date, week_number, doctor, days)
                                    if epgu_rule:
                                        doctor_rules.append(epgu_rule)
                                    days = []
                                week_number += 1

                            if timeslot['patientId'] and timeslot['patientInfo']:
                                busy_by_patients.append(
                                    dict(date_time=timeslot['start'],
                                         patient=dict(id=timeslot['patientId'], fio=timeslot['patientInfo'])
                                         ))

                        # For last iteration
                        if interval:
                            days.append(dict(date=previous_day, interval=interval))
                        if days:
                            epgu_rule = self.__post_rules(resource_id, start_date, week_number, doctor, days)
                            if epgu_rule:
                                doctor_rules.append(epgu_rule)

                        # if busy_by_patients:
                        #     self.__appoint_patients(hospital[doctor.lpuId], doctor, busy_by_patients)
        else:
            self.__log(u'Нет ни одного ЛПУ, синхронизированного с ЕПГУ')
            return False

    def activate_locations(self):
        self.__log(u'ФЭР2 не требует отдельного запуска активации очередей')

    def sync_hospitals(self):
        pass

    def sync_data(self):
        self.sync_hospitals()
        self.sync_reservation_types()
        self.sync_payment_methods()
        self.sync_specialities()
        self.sync_locations()
        self.sync_schedule()

    def __parse_hl7(self, message):
        add_code = ['SRM', 'S01', 'SRM_S01']
        del_code = ['SRM', 'S04', 'SRM_S01']
        result = dict()
        data = hl7.parse(message)
        if data:
            operation_code = data['MSH'][0][8]
            if cmp(operation_code, add_code) == 0:
                operation = 'add'
                slot_id = data['ARQ'][0][1][0]
                timeslot = datetime.datetime.strptime(data['ARQ'][0][11][0], '%Y%m%d%H%M%S')
                lastName = data['PID'][0][5][0]
                firstName = data['PID'][0][5][1]
                patronymic = data['PID'][0][5][2]
                if not lastName or not firstName:
                    return None
                patient = self.Struct(lastName=lastName,
                                      firstName=firstName,
                                      patronymic=patronymic)
                doctor_keyEPGU = data['AIP'][0][3][0]
                result = dict(operation=operation,
                              slot_id=slot_id,
                              timeslot=timeslot,
                              patient=patient,
                              doctor_keyEPGU=doctor_keyEPGU)

            elif cmp(operation_code, del_code) == 0:
                operation = 'delete'
                slot_id = data['ARQ'][0][2][0]

                result = dict(operation=operation,
                              slot_id=slot_id)
        return result

    def __parse_xml(self, message):
        return None

    def __add_by_epgu(self, params):
        try:
            doctor = self.session.query(Personal).filter(
                Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU == params.get('doctor_keyEPGU'))
            ).one()

            hospital_param = dict(auth_token=doctor.lpu.token, place_id=doctor.lpu.keyEPGU)
        except MultipleResultsFound, e:
            print e
            logger.error(e, extra=logger_tags)
        except NoResultFound, e:
            print e
            logger.error(e, extra=logger_tags)
            return None
        else:
            slot_id = params.get('slot_id')
            print 'add_by_epgu %s' % slot_id
            if slot_id:
                ticket_exists = self.session.query(Enqueue).filter(Enqueue.keyEPGU == slot_id).count()
                if ticket_exists:
                    logger.error(u'Запись пациента, инициированная ЕПГУ ({0}). '
                                 u'Запись не осуществлена: '
                                 u'талончик с keyEPGU={1} уже существует'.format(params, slot_id),
                                 extra=logger_tags)
                    return False

            enqueue_dw = DataWorker.provider('enqueue', self.session)
            _enqueue = enqueue_dw.enqueue(
                person=params.get('patient'),
                hospitalUid='%i/%i' % (doctor.lpuId, doctor.orgId),
                doctorUid=doctor.doctor_id,
                timeslotStart=params.get('timeslot'),
                epgu_slot_id=slot_id
            )
            if _enqueue and _enqueue['result'] is True:
                logger.debug(u'Запись пациента, инициированная ЕПГУ ({0}). '
                             u'Запись успешна.'.format(params),
                             extra=logger_tags)
                return True
            else:
                self.epgu_delete_slot(
                    hospital=hospital_param,
                    slot_id=params.get('slot_id'))

    def send_enqueue(self, hospital, doctor, patient, timeslot, enqueue_id, slot_unique_key):
        print 'send_enqueue %s' % slot_unique_key
        print 'enqueue_id %s' % enqueue_id
        print 'hospital_auth_token: %s | hospital_place_id: %s' % (hospital['auth_token'], hospital['place_id'])
        if not slot_unique_key:
            if not hospital['auth_token'] or not hospital['place_id']:
                return None

            _patient = dict(firstName=patient['fio']['firstName'],
                            lastName=patient['fio']['lastName'],
                            patronymic=patient['fio']['patronymic'],
                            id=patient['id'])

            slot_unique_key = self.epgu_appoint_patient(hospital=hospital,
                                                        doctor=doctor,
                                                        patient=_patient,
                                                        timeslot=timeslot)
            print slot_unique_key
        if slot_unique_key:
            enqueue_dw = DataWorker.provider('enqueue', self.session)
            _enqueue = enqueue_dw.update_enqueue(enqueue_id, dict(keyEPGU=slot_unique_key))
            print '_enqueue %s' % _enqueue

    def __delete_by_epgu(self, params):
        try:
            enqueue = self.session.query(Enqueue).filter(Enqueue.keyEPGU == params.get('slot_id')).one()
        except MultipleResultsFound, e:
            print e
            logger.error(e, extra=logger_tags)
            return None
        except NoResultFound, e:
            print e
            logger.error(e, extra=logger_tags)
            return None
        else:
            data = json.loads(enqueue.Data)
            result = None
            logger.debug(u'Удаление записи, инициированное ЕПГУ ({0}).'.format(params),
                         extra=logger_tags)
            if data['hospitalUid']:
                enqueue_dw = DataWorker.provider('enqueue', self.session)
                result = enqueue_dw.dequeue(hospitalUid=data['hospitalUid'],
                                            ticketUid='%s/%s' % (enqueue.ticket_id, enqueue.patient_id))
        return result

    def epgu_request(self, format, message):
        result = None
        data = None
        message = message.decode('utf-8')
        # TODO: повесить на celery, если ЕПГУ не нужен мгновенный ответ (просто дать ответ, а выполнить асинхронно)
        if format == 'HL7':
            data = self.__parse_hl7(message)
        elif format == 'XML':
            data = self.__parse_xml(message)

        if data:
            if data.get('operation') == 'add':
                result = self.__add_by_epgu(data)
            elif data.get('operation') == 'delete':
                result = self.__delete_by_epgu(data)
        return result

    # SYNC SCHEDULE TASKS
    def appoint_patients(self, patient_slots, hospital, doctor):
        if not patient_slots:
            return None
        for patient_slot in patient_slots:
            try:
                service_type = doctor.speciality[0].epgu_service_type
                service_type_keyEPGU = service_type.keyEPGU
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
                continue
            fio_list = patient_slot['patient']['fio'].split()
            patient = dict(firstName=fio_list[1], lastName=fio_list[0], id=patient_slot['patient']['id'])
            try:
                patronymic = fio_list[2]
            except IndexError, e:
                print e
                logger.error(e, extra=logger_tags)
                patient['patronymic'] = u''
            else:
                patient['patronymic'] = patronymic

            key_epgu = self.session.query(Personal_KeyEPGU).filter(
                Personal_KeyEPGU.lpuId == doctor.lpuId,
                Personal_KeyEPGU.orgId == doctor.orgId,
                Personal_KeyEPGU.doctor_id == doctor.doctor_id
            ).one()
            self.epgu_appoint_patient(
                hospital=hospital,
                doctor=dict(location_id=key_epgu.keyEPGU, epgu_service_type=service_type_keyEPGU),
                patient=patient,
                timeslot=patient_slot['date_time']
            )

    def activate_location(self, hospital, location_id):
        epgu_result = self.proxy_client.PutActivateLocation(hospital, location_id)
        location = getattr(epgu_result, 'location', None)
        if location:
            self.__log(u'Очередь %s (%s) активирована' % (location.prefix, location.id))
        else:
            self.__log(getattr(epgu_result, 'error', None))

    def link_schedule(self, rules, hospital, location_id):
        if not rules:
            return None
        print (hospital, location_id, rules)
        epgu_result = self.proxy_client.PutLocationSchedule(
            hospital,
            location_id,
            rules)
        applied_schedule = getattr(epgu_result, 'applied-schedule', None)
        print applied_schedule
        if applied_schedule:
            applied_rules = getattr(applied_schedule, 'applied-rules', None)
            if applied_rules:
                applied_rule = getattr(applied_rules, 'applied-rule')
                if isinstance(applied_rule, list):
                    for _applied_rule in applied_rule:
                        self.__log(
                            u'Очереди (%s) назначено расписание с %s по %s (%s)' %
                            (getattr(applied_schedule, 'location-id', ''),
                             getattr(_applied_rule, 'start-date'),
                             getattr(_applied_rule, 'end-date'),
                             getattr(_applied_rule, 'rule-id')))
                else:
                    if applied_rule:
                        self.__log(
                            u'Очереди (%s) назначено расписание с %s по %s (%s)' %
                            (getattr(applied_schedule, 'location-id', ''),
                             getattr(applied_rule, 'start-date'),
                             getattr(applied_rule, 'end-date'),
                             getattr(applied_rule, 'rule-id')))
        else:
            self.__log(getattr(epgu_result, 'error', None))
        return self.msg

    def doctor_schedule_task(self, doctor, hospital_dict):
        today = datetime.datetime.today().date()
        # TODO: get nearest monday for start_date?
        start_date = today - datetime.timedelta(days=(today.isoweekday() - 1))  # + datetime.timedelta(weeks=1)
        end_date = start_date + datetime.timedelta(weeks=self.schedule_weeks_period)
        enqueue_dw = DataWorker.provider('enqueue', self.session)
        params = {
            'hospitalUid': '%s/%s' % (doctor.lpuId, doctor.orgId),
            'doctorUid': doctor.doctor_id,
            'startDate': start_date,
            'endDate': end_date,
            }
        location_id = doctor.key_epgu.keyEPGU

        schedule = enqueue_dw.get_info(**params)
        doctor_rules = []
        busy_by_patients = []
        if schedule:
            days = []
            interval = []
            week_number = 1
            previous_day = None
            for timeslot in schedule['timeslots']:
                #TODO: понять, как будет с Интрамедом
                if timeslot['status'] == 'disabled':
                    continue

                if previous_day is not None and previous_day.date() != timeslot['start'].date():
                    days.append(dict(date=previous_day, interval=interval))
                    interval = []

                interval.append(dict(start=timeslot['start'].time().strftime('%H:%M'),
                                     end=timeslot['finish'].time().strftime('%H:%M')))

                previous_day = timeslot['start']

                if timeslot['start'].date() >= (start_date + datetime.timedelta(weeks=week_number)):
                    if days:
                        epgu_rule = self.__post_rules(start_date, week_number, hospital_dict, doctor, days)
                        if epgu_rule:
                            doctor_rules.append(epgu_rule)
                        days = []
                    week_number += week_number

                if timeslot['patientId'] and timeslot['patientInfo']:
                    busy_by_patients.append(
                        dict(date_time=timeslot['start'],
                             patient=dict(id=timeslot['patientId'], fio=timeslot['patientInfo'])
                        ))

            # For last iteration
            if interval:
                days.append(dict(date=previous_day, interval=interval))
            if days:
                epgu_rule = self.__post_rules(start_date, week_number, hospital_dict, doctor, days)
                if epgu_rule:
                    doctor_rules.append(epgu_rule)

            # if doctor_rules:
            #     self.__link_activate_schedule(hospital_dict, location_id, doctor_rules)
            #
            # if busy_by_patients:
            #     self.__appoint_patients(hospital_dict, doctor, busy_by_patients)

        return doctor_rules, busy_by_patients

    def get_doctor_tickets(self, doctor):
        today = datetime.datetime.today().date()
        # TODO: get nearest monday for start_date?
        start_date = today - datetime.timedelta(days=(today.isoweekday() - 1))  # + datetime.timedelta(weeks=1)
        end_date = start_date + datetime.timedelta(weeks=self.schedule_weeks_period)
        enqueue_dw = DataWorker.provider('enqueue', self.session)
        params = {
            'hospitalUid': '%s/%s' % (doctor.lpuId, doctor.orgId),
            'doctorUid': doctor.doctor_id,
            'startDate': start_date,
            'endDate': end_date,
        }

        schedule = enqueue_dw.get_info(**params)
        busy_by_patients = []
        if schedule:
            for timeslot in schedule['timeslots']:
                #TODO: понять, как будет с Интрамедом
                if timeslot['status'] == 'disabled':
                    continue

                if timeslot['patientId'] and timeslot['patientInfo']:
                    busy_by_patients.append(
                        dict(date_time=timeslot['start'],
                             patient=dict(id=timeslot['patientId'], fio=timeslot['patientInfo'])
                        ))

        return busy_by_patients

    def _save_ticket(self, lpu_id, ticket, message=None, data=None):
        try:
            _ticket = Tickets()
            _ticket.lpu_id = lpu_id
            _ticket.doctor_id = ticket.personId
            _ticket.patient_id = ticket.patient.id
            _ticket.timeslot = datetime.datetime.utcfromtimestamp(ticket.begDateTime / 1000)
            _ticket.ticket_uuid = ticket.uuid
            if message:
                _ticket.message = message
            if data:
                _ticket.data = data
            self.session.add(_ticket)
        except exceptions.Exception, e:
            print e
            logger.error(e, extra=logger_tags)
            self.session.rollback()
            return None
        else:
            self.session.commit()
            return _ticket

    def _get_ticket(self, lpu_id, doctor_id, ticket_uid):
        ticket = self.session.query(Tickets).filter(Tickets.lpu_id == lpu_id,
                                                    Tickets.doctor_id == doctor_id,
                                                    Tickets.ticket_uuid == ticket_uid).first()
        return ticket

    def send_new_tickets(self, hospital_id, hospital_info):
        person_dw = DataWorker.provider('personal')
        enqueue_dw = DataWorker.provider('enqueue')
        tickets = enqueue_dw.get_new_tickets(hospital_id)
        task_hospital = hospital_info  # dict(auth_token=lpu_info.token, place_id=lpu_info.keyEPGU)
        if tickets:
            for ticket in tickets:
                if ticket.status == CouponStatus.NEW:
                    _ticket = self._save_ticket(hospital_id, ticket)
                    if _ticket:
                        doctor_info = person_dw.get_doctor(lpu_unit=[hospital_id, 0], doctor_id=ticket.personId)
                        service_type = doctor_info.speciality[0].epgu_service_type
                        task_doctor = dict(location_id=getattr(doctor_info.key_epgu, 'keyEPGU', None),
                                           epgu_service_type=getattr(service_type, 'keyEPGU', None))


                        _patient = dict(firstName=ticket.patient.firstName,
                                        lastName=ticket.patient.lastName,
                                        patronymic=ticket.patient.patrName,
                                        id=ticket.patient.id)
                        timeslot = datetime.datetime.utcfromtimestamp(ticket.begDateTime / 1000)
                        slot_unique_key = self.epgu_appoint_patient(hospital=task_hospital,
                                                                    doctor=task_doctor,
                                                                    patient=_patient,
                                                                    timeslot=timeslot)
                        _ticket.keyEPGU = slot_unique_key
                        self.session.commit()
                elif ticket.status == CouponStatus.CANCELLED:
                    _ticket = self._get_ticket(hospital_id, ticket.personId, ticket.uuid)
                    self.epgu_delete_slot(task_hospital, _ticket.keyEPGU)


    # def lpu_schedule_task(self, hospital_id, hospital_dict):
    #     epgu_doctors = self.session.query(Personal).filter(Personal.lpuId == hospital_id).filter(
    #         Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU != None)
    #     ).all()
    #     obj = EPGUWorker()
    #     if epgu_doctors:
    #         group(
    #             [chain(
    #                 obj.doctor_schedule_task.s(doctor, hospital_dict),
    #                 obj.link_schedule.s(hospital_dict, doctor.key_epgu.keyEPGU),
    #                 obj.activate_location.s(hospital_dict, doctor.key_epgu.keyEPGU).set(countdown=5),
    #                 obj.appoint_patients.s(hospital_dict, doctor.key_epgu.keyEPGU).set(countdown=5)
    #             ) for doctor in epgu_doctors])()
    #
    # def sync_schedule_task(self):
    #     lpu_list = (self.session.query(LPU).
    #                 filter(LPU.keyEPGU != '',
    #                        LPU.keyEPGU != None,
    #                        LPU.token != '',
    #                        LPU.token != None).
    #                 all())
    #     if lpu_list:
    #         obj = EPGUWorker()
    #         res = group([
    #             obj.lpu_schedule_task.s(
    #                 lpu.id,
    #                 dict(auth_token=lpu.token, place_id=lpu.keyEPGU)
    #             ) for lpu in lpu_list])()
    #         # print res.get()
    #         # print self.msg
    #     else:
    #         self.__log(u'Нет ни одного ЛПУ, синхронизированного с ЕПГУ')
    #         return False
