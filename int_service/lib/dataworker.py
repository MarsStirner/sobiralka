# -*- coding: utf-8 -*-

import exceptions
import urllib2
import datetime, time
try:
    import json
except ImportError:
    import simplejson as json

from sqlalchemy import or_, and_
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.exc import InvalidRequestError
from suds import WebFault

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT
from admin.models import LPU, LPU_Units, UnitsParentForId, Enqueue, Personal, Speciality, Regions
from service_clients import Clients
from is_exceptions import exception_by_code, IS_ConnectionError

from admin.database import Session, shutdown_session


class DataWorker(object):
    """Provider class for current DataWorkers"""
    @classmethod
    def provider(cls, type):
        """Вернёт объект для работы с указанным типом данных"""
        type = type.lower()
        if type == 'regions':
            obj = RegionsWorker()
        elif type == 'lpu':
            obj = LPUWorker()
        elif type == 'lpu_units':
            obj = LPU_UnitsWorker()
        elif type == 'enqueue':
            obj = EnqueueWorker()
        elif type == 'personal':
            obj = PersonalWorker()
        else:
            obj = None
            raise exceptions.NameError
        return obj


class RegionsWorker(object):
    """Класс для работы с информацией по регионам"""
    session = Session()
    # session.autocommit = True
    model = Regions

    def __del__(self):
        self.session.close()

    def get_list(self):
        """Возвращает список регионов"""
        return self.session.query(Regions).filter(Regions.is_active == True).order_by(Regions.name).all()


class LPUWorker(object):
    """Класс для работы с информацией по ЛПУ"""
    session = Session()
    # session.autocommit = True
    model = LPU

    def __del__(self):
        self.session.close()

    @classmethod
    def parse_hospital_uid(cls, hospitalUid):
        """Парсит uid ЛПУ, извлекая id ЛПУ и id подразделения

        Args:
            hospitalUid: строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID'

        """
        lpu = []
        lpu_units = []
        if not isinstance(hospitalUid, list):
            hospitalUid = [hospitalUid, ]
        for i in hospitalUid:
            tmp_list = i.split('/')
            if len(tmp_list) > 1 and int(tmp_list[1]):
                lpu_units.append([int(tmp_list[0]), int(tmp_list[1])])
            else:
                lpu.append(int(tmp_list[0]))
        return lpu, lpu_units

    def get_list(self, **kwargs):
        """Возвращает список ЛПУ

        Args:
            id: массив id ЛПУ для фильтрации (необязательный)
            speciality: врачебная специальность для фильтрации ЛПУ (необязательный)
            okato_code: код ОКАТО для фильтрации ЛПУ (необязательный)

        """
        lpu_ids = kwargs.get('id')
        speciality = kwargs.get('speciality')
        okato_code = kwargs.get('okato_code')

        # Prepare query for getting LPU
#        fields = [LPU.id, LPU.name, LPU.phone, LPU.address, LPU.key, LPU.proxy, LPU.token, LPU.protocol]
        fields = [LPU]
        filter = []
        join = []

        if speciality and isinstance(speciality, unicode):
            fields.append(Personal.speciality)

        query_lpu = self.session.query(*fields)

        if speciality and isinstance(speciality, unicode):
            query_lpu = query_lpu.join(Personal)
            query_lpu = query_lpu.filter(Personal.speciality == speciality)

        if lpu_ids and len(lpu_ids):
            query_lpu = query_lpu.filter(LPU.id.in_(lpu_ids))

        if okato_code:
            query_lpu = query_lpu.filter(LPU.OKATO.like('%' + okato_code + '%'))

        return query_lpu.all()

    def get_lpu_by_address(self, **kwargs):
        """Возвращает список ЛПУ для указанного адреса пациента

        Args:
            parsedAddress: словарь вида,
                {'kladrCode': КЛАДР код населенного пункта,
                 'flat': номер квартиры,
                 'house': {
                    'number': номер дома,
                    'building': литера, корпус, строение, (необязательный)
                 },
                }

        """
        try:
            if (kwargs['parsedAddress']['kladrCode']
                #and kwargs['parsedAddress']['block']
                and kwargs['parsedAddress']['flat']
                #and kwargs['parsedAddress']['house']['building']
                and kwargs['parsedAddress']['house']['number']):
                    # Prepare search parameters
                    streetKLADR = kwargs.get('parsedAddress', {}).get('kladrCode')
                    pointKLADR = kwargs.get('parsedAddress').get('kladrCode')[0:5].ljust(15, '0')
        except exceptions.AttributeError:
            return []

        result = []

        lpu_list = kwargs.get('lpu_list')
        if lpu_list:
            used_proxy = []
            # Use LPU proxy for searching by SOAP
            for lpu in lpu_list:
                proxy = lpu.proxy.split(';')
                if proxy[0] and proxy[0] not in used_proxy:
                    used_proxy.append(proxy[0])
                    proxy_client = Clients.provider(lpu.protocol, proxy[0])
                    result.append(proxy_client.findOrgStructureByAddress({
                        'serverId': lpu.key,
                        'number': kwargs.get('parsedAddress').get('house').get('number'),
                        'corpus': kwargs.get('parsedAddress').get('house', {}).get('building'),
                        'pointKLADR': pointKLADR,
                        'streetKLADR': streetKLADR,
                        'flat': kwargs.get('parsedAddress').get('flat'),
                    }))

        if result:
            result = self._get_lpu_ids(result)

        return result

    def _get_lpu_ids(self, lpu_list):
        """
        Get ids and OrgIds by lpu data list
        lpu_list contains info from `findOrgStructureByAddress` remote method
        """
        for key, item in lpu_list:
            query = (self.session.query(UnitsParentForId.OrgId, LPU.id)
                     .filter(UnitsParentForId.LpuId == LPU.id)
                     .filter(LPU.key == item['serverId'])
                     .filter(UnitsParentForId.ChildId == int(item['orgStructureId'])))
            try:
                lpu_ids = query.one()
            except MultipleResultsFound, e:
                print e
            else:
                lpu_list[key]['id'] = lpu_ids.id
                lpu_list[key]['OrgId'] = lpu_ids.OrgId

        return lpu_list

    def get_list_hospitals(self, **kwargs):
        """Формирует и возвращает список ЛПУ и подразделений для SOAP

        Args:
            hospitalUid: строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный)
            speciality: врачебная специальность для фильтрации ЛПУ (необязательный)
            ocatoCode: код ОКАТО для фильтрации ЛПУ (необязательный)

        """
        result = dict()
        result['hospitals'] = []
        lpu = []
        lpu_units = []

        hospital_uid = kwargs.get('hospitalUid')

        if hospital_uid:
            lpu, lpu_units = LPUWorker.parse_hospital_uid(hospital_uid)

        speciality = kwargs.get('speciality')
        okato_code = kwargs.get('ocatoCode')

        lpu_list = self.get_list(id=lpu, speciality=speciality, okato_code=okato_code)
        # Append LPUs to result
        for item in lpu_list:
            result['hospitals'].append({
                'uid': str(item.id) + '/0',
                'name': item.name,
                'phone': item.phone,
                'address': item.address,
                'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + str(SOAP_SERVER_PORT) + '/schedule/?wsdl',
                'token': item.token,
                'key': item.key,
            })

        if not okato_code:
            units_dw = LPU_UnitsWorker()
            lpu_units_list = units_dw.get_list(uid=lpu_units, speciality=speciality)
            # Append LPU_Units to result
            for item in lpu_units_list:
                uid = str(item.lpuId) + '/' + str(item.orgId)
                # TODO: проверить работоспособность item.parent
                if item.parent:
                    uid += '/' + str(item.parent.id)
                else:
                    uid += '/0'

                result['hospitals'].append({
                    'id': item.orgId,
                    'uid': uid,
                    'name': item.name,
                    'phone': item.lpu.phone,
                    'address': item.address,
                    # TODO: выяснить используется ли wsdlURL и верно ли указан
                    'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + str(SOAP_SERVER_PORT) + '/schedule/?wsdl',
                    'token': item.lpu.token,
                    'key': item.lpu.key,
                })
        shutdown_session()
        return result

    def get_info(self, **kwargs):
        """Возвращает список ЛПУ и подразделений по переданным параметрам

        Args:
            hospitalUid: строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный)

        """
        lpu, lpu_units = [], []
        result = []

        hospital_uid = kwargs.get('hospitalUid')
        if hospital_uid:
            lpu, lpu_units = self.parse_hospital_uid(hospital_uid)

        lpu_units_dw = LPU_UnitsWorker()

        for lpu_item in self.get_list(id=lpu):
            units = []
            for lpu_units_item in lpu_units_dw.get_list(uid=lpu_units, lpu_id=lpu_item.id):
                uid = str(lpu_units_item.lpuId) + '/' + str(lpu_units_item.orgId)
                if lpu_units_item.parent:
                    uid += '/' + str(lpu_units_item.parent.OrgId)
                else:
                    uid += '/0'

                units.append({
                    'id': lpu_units_item.orgId,
                    'uid': uid,
                    'name': lpu_units_item.name,
                    'address': lpu_units_item.address,
                    'phone': lpu_item.phone,
                    'schedule': lpu_item.schedule,
                })

            result.append({
                'uid': str(lpu_item.id) + '/0',
                'name': lpu_item.name,
                'type': lpu_item.type,
                'phone': lpu_item.phone,
                'email': lpu_item.email,
                'siteURL': '',
                'schedule': lpu_item.schedule,
                'buildings': units,
            })
        shutdown_session()
        return {'info': result}

    def get_by_id(self, id):
        """
        Get LPU by id and check if proxy url is available
        """
        try:
            result = self.session.query(LPU).filter(LPU.id == int(id)).one()
        except NoResultFound, e:
            print e
        else:
            result.proxy = result.proxy.split(';')[0]
            if result.protocol in ('intramed', 'samson', 'korus20'):
                # Проверка для soap-сервисов на доступность, неактуально для thrift (т.е. для korus30)
                if urllib2.urlopen(result.proxy).getcode() == 200:
                    return result
                else:
                    raise WebFault
            else:
                return result
        return None

    def get_uid_by_code(self, code):
        """
        Get LPU.uid by code
        """
        try:
            result = self.session.query(LPU.id).filter(LPU.key == code).one()
        except NoResultFound, e:
            print e
        except MultipleResultsFound, e:
            print e
        else:
            return result
        return None


class LPU_UnitsWorker(object):
    """Класс для работы с информацией по подразделениям"""
    session = Session()
    # session.autocommit = True
    model = LPU_Units

    def __del__(self):
        self.session.close()

    def get_list(self, **kwargs):
        """Возвращает список подразделений

        Args:
            uid: массив uid подразделений (необязательный)
            lpu_id: массив id ЛПУ для фильтрации (необязательный)
            speciality: врачебная специальность для фильтрации подразделений (необязательный)

        """
        lpu_units_ids = kwargs.get('uid')
        speciality = kwargs.get('speciality')
        lpu_id = kwargs.get('lpu_id')

        # Prepare query for getting LPU_Units
#        fields = [LPU_Units.id, LPU_Units.lpuId, LPU_Units.name, LPU_Units.address,
#                  LPU.phone, LPU.token, LPU.key, UnitsParentForId.LpuId.label('parentId')]
        fields = [LPU_Units]
        filter = []
        _join = []
        or_list = []

        if speciality and isinstance(speciality, unicode):
            fields.append(Personal.speciality)
            _join.append(Personal)

        query_lpu_units = self.session.query(*fields)

        if _join:
            for i in _join:
                query_lpu_units = query_lpu_units.join(i)

        query_lpu_units = query_lpu_units.outerjoin(LPU_Units.lpu)
        query_lpu_units = query_lpu_units.outerjoin(LPU_Units.parent, aliased=True)
        #.filter(LPU_Units.lpuId == UnitsParentForId.OrgId)

        if len(lpu_units_ids):
            for unit in lpu_units_ids:
                or_list.append(and_(LPU_Units.lpuId == unit[0], LPU_Units.orgId == unit[1]))
            query_lpu_units = query_lpu_units.filter(or_(*or_list))

        if speciality and isinstance(speciality, unicode):
            query_lpu_units = query_lpu_units.filter(Personal.speciality == speciality)

        if lpu_id:
            query_lpu_units = query_lpu_units.filter(LPU_Units.lpuId == lpu_id)

        return query_lpu_units.group_by(LPU_Units.id).all()

    def get_by_id(self, id):
        """
        Get LPU_Unit by id
        """
        try:
            result = self.session.query(LPU_Units).filter(LPU_Units.id==int(id)).one()
        except NoResultFound, e:
            print e
        else:
            return result
        return None


class EnqueueWorker(object):
    session = Session()
    # session.autocommit = True
    model = Enqueue
    SCHEDULE_DAYS_DELTA = 14

    def __del__(self):
        self.session.close()

    def get_info(self, **kwargs):
        """Возвращает информацию о расписании

        Args:
            hospitalUid: uid ЛПУ, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            doctorUid: uid врача (обязательный)
            speciality: наименование врачебной специальности (необязательный)
            hospitalUidFrom: uid ЛПУ, из которого производилась запись (необязательный)

        """
        result = {}

        hospital_uid = kwargs.get('hospitalUid', '').split('/')
        if isinstance(hospital_uid, list) and len(hospital_uid) > 1:
            lpu_dw = LPUWorker()
            lpu = lpu_dw.get_by_id(hospital_uid[0])
        else:
            shutdown_session()
            raise exceptions.ValueError
            return {'timeslots': []}

        if 'doctorUid' in kwargs:
            doctor_uid = int(kwargs.get('doctorUid'))
        else:
            shutdown_session()
            raise exceptions.KeyError
            return {'timeslots': []}

        speciality = kwargs.get('speciality')
        if not speciality:
            personal_dw = PersonalWorker()
            doctor = personal_dw.get_doctor(doctor_id=doctor_uid, lpu_unit=hospital_uid)
            if doctor:
                speciality = doctor.speciality

        hospital_uid_from = kwargs.get('hospitalUidFrom', 0)
        start, end = self.__get_dates_period(kwargs.get('startDate'), kwargs.get('endDate'))

        proxy_client = Clients.provider(lpu.protocol, lpu.proxy.split(';')[0])
        params = {
            'hospital_uid': hospital_uid,
            'doctor_uid': doctor_uid,
            'start': start,
            'end': end,
            'speciality': speciality,
            'hospital_uid_from': hospital_uid_from,
            'server_id': lpu.key
        }
        result = proxy_client.getScheduleInfo(**params)
        shutdown_session()
        return result

    def __get_dates_period(self, start, end):
        if not start:
            start = datetime.date.today()
        if not end:
            end = (start + datetime.timedelta(days=self.SCHEDULE_DAYS_DELTA))
        return start, end

    def __get_tickets_ge_id(self, id, hospital_uid=None):
        tickets = []
        for item in self.session.query(Enqueue).filter(
            Enqueue.DataType == '0',
            Enqueue.id > id,
            Enqueue.Error == '100 ok',
            Enqueue.status == 0
        ):
            data = json.load(item.Data)
            if hospital_uid and hospital_uid == data['hospitalUid'] or hospital_uid is None:
                tickets.append({
                    'id': item.id,
                    'data': data,
                    'error': item.error,
                })
        return tickets

    def get_by_id(self, id):
        """Возвращает талончик по id

        Args:
            id: id талончика

        """
        try:
            result = self.session.query(Enqueue).filter(Enqueue.id==int(id)).one()
        except NoResultFound, e:
            print e
        else:
            return result
        return None

    def get_ticket_status(self, **kwargs):
        """Возвращает статус талончика

        Args:
            hospitalUid: uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            ticketUid: uid талончика (обязательный), строка вида 'ticket_id/patient_id'
            lastUid: id талончика, начиная с которого необходимо сделать выборку информации о талончиках,
                если передан, то ticketUid игнорируется (необязательный)

        """
        result = dict()
        result['ticketInfo'] = []
        hospital_uid = kwargs.get('hospitalUid', '').split('/')
        ticket_uid = kwargs.get('ticketUid')
        if hospital_uid and ticket_uid:
            if len(hospital_uid) > 1:
                if hospital_uid[1]:
                    # It's lpu_unit, work with LPU_UnitsWorker
                    dw = LPU_UnitsWorker()
                    lpu_info = dw.get_by_id(hospital_uid[1])
                    lpu_address = lpu_info.address
                    lpu_name = lpu_info.name + '(' + lpu_info.lpu.name + ')'
                    proxy_client = Clients.provider(lpu_info.lpu.protocol, lpu_info.lpu.proxy.split(';')[0])
                    server_id = lpu_info.lpu.key
                else:
                    # It's lpu, works with LPUWorker
                    dw = LPUWorker()
                    lpu_info = dw.get_by_id(hospital_uid[0])
                    lpu_address = lpu_info.address
                    lpu_name = lpu_info.name
                    proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
                    server_id = lpu_info.key
            else:
                shutdown_session()
#                raise exceptions.AttributeError
                return result
        else:
            shutdown_session()
            raise exceptions.KeyError
            return {}

        last_uid = kwargs.get('lastUid')

        if last_uid:
            tickets = self.__get_tickets_ge_id(last_uid, hospital_uid)
        else:
            if isinstance(ticket_uid, list):
                tickets = ticket_uid
            else:
                tickets = [ticket_uid,]

        doctor_dw = PersonalWorker()
        if tickets:
            for ticket in tickets:
                # TODO: разнести по отдельным методам
                if isinstance(ticket, dict):
                    # Working on case where kwargs['lastUid']
                    ticket_data = ticket['data']

                    # For low code dependence get current hospital_uid
                    _hospital_uid = ticket_data['hospital_uid'].split('/')

                    doctor = doctor_dw.get_doctor(lpu_unit=_hospital_uid, doctor_id=ticket_data['doctorUid'])
                    result['ticketInfo'].append({
                        'id': ticket['id'],
                        'ticketUid': ticket_data['ticketUid'],
                        'hospitalUid': ticket_data['hospitalUid'],
                        'doctorUid': ticket_data['doctorUid'],
                        'doctor': {
                            'firstName': doctor.get('firstName', ''),
                            'patronymic': doctor.get('patronymic', ''),
                            'lastName': doctor.get('lastName', ''),
                        },
                        'person': {
                            'firstName': '',
                            'patronymic': '',
                            'lastName': '',
                        },
                        'status': 'forbidden',
                        'timeslotStart': datetime.datetime.strptime(ticket_data['timeslotStart'], '%Y-%m-%dT%H:%M:%S'),
                        'comment': str(exception_by_code(ticket.get('Error'))),
                        'location': lpu_name + " " + lpu_address,
                    })

                else:

                    ticket_uid, patient_id = ticket.split('/')

                    queue_info = proxy_client.getPatientQueue({'serverId': server_id, 'patientId': patient_id})
                    patient_info = proxy_client.getPatientQueue({'serverId': server_id, 'patientId': patient_id})

                    for ticket_info in queue_info:
                        if ticket_info.queueId == ticket_uid:
                            doctor = doctor_dw.get_doctor(lpu_unit=hospital_uid, doctor_id=ticket_info['personId'])

                            if ticket_info['enqueuePersonId']:
                                # TODO: проверить действительно ли возвращаемый enqueuePersonId - это office
                                office = ticket_info['enqueuePersonId']
                            else:
                                work_times = proxy_client.getWorkTimeAndStatus({
                                    'serverId': server_id,
                                    'personId': ticket_info['personId'],
                                    'date': ticket_info['enqueueDate'],
                                })
                                if work_times:
                                    office = work_times[0].get('office')

                            _ticket_date = datetime.datetime.strptime(
                                ticket_info['date'] + ticket_info['time'], '%Y-%m-%d %H:%M:%S'
                            )

                            document = self.__get_ticket_print({
                                'name': lpu_name,
                                'address': lpu_address,
                                'fio': ' '.join((
                                    patient_info['lastName'],
                                    patient_info['firstName'][0:1] + '.',
                                    patient_info['patrName'][0:1] + '.'
                                    )),
                                'person': ' '.join((
                                    doctor.get('lastName', ''),
                                    doctor.get('firstName', ''),
                                    doctor.get('patronymic', '')
                                    )),
                                'date_time':_ticket_date,
                                'office': office,
                            })

                            result['ticketInfo'].append({
                                'id': '',
                                'ticketUid': ticket,
                                'hospitalUid': hospital_uid,
                                'doctorUid': ticket_info['personId'],
                                'doctor': {
                                    'firstName': doctor.get('firstName', ''),
                                    'patronymic': doctor.get('patronymic', ''),
                                    'lastName': doctor.get('lastName', ''),
                                    },
                                'person': {
                                    'firstName': patient_info.get('firstName'),
                                    'patronymic': patient_info.get('patrName'),
                                    'lastName': patient_info.get('lastName'),
                                    },
                                'status': 'accepted',
                                'timeslotStart': _ticket_date,
#                                'comment': exception_by_code(ticket_info.Error),
                                'location': 'кабинет:' + office + ' ' + lpu_address,
                                'printableDocument': {
                                    'printableVersionTitle': 'Талон',
                                    'printableVersion': document.encode('base64'),
                                    'printableVersionMimeType': 'application/pdf',
                                }
                                })

        shutdown_session()
        return result

    def __get_ticket_print(self, **kwargs):
        """
        Return generated pdf for ticket print
        !NOT USED
        """
        # TODO: выяснить используется ли pdf в принципе. В эл.регестратуре он никак не используется
        # TODO: pdf creator based on Flask templates and xhtml2pdf
        return ""

    def enqueue(self, **kwargs):
        """Запись на приём к врачу

        Args:
            person: { ФИО пациента (обязательный)
                'firstName'
                'lastName'
                'patronymic'
            }
            hospitalUid: uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            birthday: дата рождения пациента (обязательный)
            doctorUid: id врача, к которому производится запись (обязательный)
            omiPolicyNumber: номер полиса мед. страхования (обязательный)
            sex: пол (необязательный)
            timeslotStart: время записи на приём (обязательный)
            hospitalUidFrom: uid ЛПУ, с которого производится запись (необязательный), используется для записи между ЛПУ

        """
        hospital_uid = kwargs.get('hospitalUid', '').split('/')
        birthday = kwargs.get('birthday')
        doctor_uid = kwargs.get('doctorUid')
        person = kwargs.get('person')
        sex = kwargs.get('sex')
        omi_policy_number = kwargs.get('omiPolicyNumber')
        if omi_policy_number:
            omi_policy_number = omi_policy_number.strip()
        document_obj = kwargs.get('document')
        document = dict()
        if document_obj:
            if document_obj.client_id:
                document['client_id'] = document_obj.client_id
            if document_obj.policy_type:
                document['policy_type'] = document_obj.policy_type
            if document_obj.document_code:
                document['document_code'] = document_obj.document_code
            if document_obj.series:
                document['series'] = document_obj.series
            if document_obj.number:
                document['number'] = document_obj.number

        timeslot_start = kwargs.get('timeslotStart', '')

        if hospital_uid and birthday and doctor_uid and person:
            if len(hospital_uid) > 1:
                dw = LPUWorker()
                lpu_info = dw.get_by_id(hospital_uid[0])
                proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
            else:
                shutdown_session()
                raise exceptions.ValueError
                return {}
        else:
            shutdown_session()
            raise exceptions.ValueError
            return {}

        result = dict()

        person_dw = PersonalWorker()
        doctor_info = person_dw.get_doctor(lpu_unit=hospital_uid, doctor_id=doctor_uid)

        hospital_uid_from = kwargs.get('hospitalUidFrom', '0')

        if not doctor_info:
            shutdown_session()
            raise exceptions.LookupError
            return {}

        # Отправляет запрос на SOAP КС для записи пациента
        _enqueue = proxy_client.enqueue(
            serverId=lpu_info.key,
            person={
                'firstName': person.firstName,
                'lastName': person.lastName,
                'patronymic': person.patronymic,
            },
            omiPolicyNumber=omi_policy_number,
            document=document,
            birthday=birthday,
            sex=sex,
            hospitalUid=hospital_uid[1],
            hospitalUidFrom=hospital_uid_from,
            speciality=doctor_info.speciality.lower(),
            doctorUid=doctor_uid,
            timeslotStart=timeslot_start
        )

        if _enqueue and _enqueue['result'] is True:
            self.__add_ticket(
                error=_enqueue.get('error_code'),
                data=json.dumps({
                    'ticketUID': _enqueue.get('ticketUid'),
                    'timeslotStart': timeslot_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'hospitalUid': kwargs.get('hospitalUid'),
                    'doctorUid': doctor_uid,
                }),
            )
            result = {'result': _enqueue.get('result'),
                      'message': exception_by_code(_enqueue.get('error_code')),
                      'ticketUid': _enqueue.get('ticketUid')}
        else:
            enqueue_id = self.__add_ticket(
                error=_enqueue.get('error_code'),
                data=json.dumps({
                    'ticketUID': _enqueue.get('ticketUid'),
                    'timeslotStart': timeslot_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'hospitalUid': kwargs.get('hospitalUid'),
                    'doctorUid': doctor_uid,
                }),
            )
            result = {
                'result': _enqueue.get('result'),
                'message': exception_by_code(_enqueue.get('error_code')),
                'ticketUid': 'e' + str(enqueue_id)
            }

        shutdown_session()
        return result

    def __add_ticket(self, **kwargs):
        """Добавляет информацию о талончике в БД ИС"""
        try:
            enqueue = Enqueue(**kwargs)
        except exceptions.ValueError, e:
            print e
            self.session.rollback()
        else:
            self.session.add(enqueue)
            self.session.commit()
            return enqueue.id
        return None


class PersonalWorker(object):
    """Класс для работы с информацией по врачам"""
    session = Session()
    # session.autocommit = True
    model = Personal

    def __del__(self):
        self.session.close()

    def get_list(self, **kwargs):
        """Возвращает список врачей по переданным параметрам
        Если переданы параметры, то фильтрует список врачей для указанных ЛПУ и/или подразделений

        Args:
            lpu: массив объектов ЛПУ (soap_models.LPU) (необязательный)
            lpu_units: массив объектов подразделений (soap_models.LPU_Units) (необязательный)

        """
        lpu = kwargs.get('lpu')
        lpu_units = kwargs.get('lpu_units')
        speciality = kwargs.get('speciality')
        lastName = kwargs.get('lastName')
        or_list = []
        if lpu or lpu_units:
            for item in lpu:
                or_list.append(and_(Personal.lpuId == item.id,))
            for item in lpu_units:
                or_list.append(and_(Personal.lpuId == item.lpuId, Personal.orgId == item.orgId))
#         else:
                #TODO: по-хорошему бы расскоментить, чтоб при пустых параметрах была пустота, но сначала нужно изменить код НТК
# #            raise exceptions.AttributeError
#             return []

        query = self.session.query(
            Personal.FirstName,
            Personal.PatrName,
            Personal.LastName,
            Personal.speciality,
            Personal.id,
            Personal.lpuId,
            Personal.orgId,
            Personal.keyEPGU,
            LPU.name.label('lpu_name'),
            LPU_Units.name.label('lpu_units_name'),
            LPU.address.label('lpu_address'),
            LPU_Units.address.label('lpu_units_address'),
            LPU.phone,
            LPU.key,
        )

        query = query.outerjoin(LPU)
        query = query.outerjoin(LPU_Units, Personal.orgId == LPU_Units.orgId).filter(Personal.lpuId == LPU_Units.lpuId)

        if speciality:
            query = query.filter(Personal.speciality == speciality)
        if lastName:
            query = query.filter(Personal.lastName == lastName)

        query = query.filter(or_(*or_list))
        query = query.order_by(Personal.LastName, Personal.FirstName, Personal.PatrName)

        return query.all()

    def get_doctor(self, **kwargs):
        """Возвращает информацию о враче

        Args:
            doctor_id: id врача  (обязательный)
            lpu_unit: uid ЛПУ или подразделения, список вида: ['17, 0'], соответствует ['LPU_ID', 'LPU_Unit_ID'] (необязательный)

        """
        lpu_unit = kwargs.get('lpu_unit')
        doctor_id = kwargs.get('doctor_id')

        query = self.session.query(Personal)

        if lpu_unit:
            if int(lpu_unit[1]):
                query = query.filter(Personal.lpuId == int(lpu_unit[0]), Personal.orgId == int(lpu_unit[1]))
            else:
                query = query.filter(Personal.lpuId == int(lpu_unit[0]))
        if doctor_id:
            query = query.filter(Personal.id == int(doctor_id))

        return query.one()

    def get_list_doctors(self, **kwargs):
        """Формирует и возвращает список врачей для SOAP

        Args:
            {'searchScope':
                {
                'hospitalUid': uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный),
                'address': адрес пациента, для выборки ЛПУ (необязательный),
                    {'parsedAddress':
                        {'flat': номер квартиры,
                        'house':{
                            'number': Номер дома
                            'building': Указание на литеру, корпус, строение
                        }
                        'block': Номер квартала (для муниципальных образований,
                            в которых адресация зданий производится с помощью кварталов, а не улиц)
                        'kladrCode': Идентификатор по классификатору КЛАДР
                        }
                    }
                }
            'speciality': специальность врача (необязательный),
            'lastName': фамилия врача (необязательный),
            }

        """
        lpu, lpu_list, lpu_units, lpu_units_list = [], [], [], []
        search_scope = kwargs.get('searchScope')

        if search_scope:
            if hasattr(search_scope, 'hospitalUid'):
                lpu, lpu_units = LPUWorker.parse_hospital_uid(search_scope.hospitalUid)
            lpu_dw = LPUWorker()
            if lpu:
                lpu_list = lpu_dw.get_list(id=lpu)

            if hasattr(search_scope, 'address') and search_scope.address:
                # TODO: уточнить используется ли поиск по адресу
                lpu_list = lpu_dw.get_lpu_by_address(search_scope.address, lpu_list)

        if lpu_units:
            lpu_units_dw = LPU_UnitsWorker()
            lpu_units_list = lpu_units_dw.get_list(uid=lpu_units)

        result = dict()
        result['doctors'] = []
        result['hospitals'] = []

        query_result = self.get_list(
            lpu=lpu_list,
            lpu_units=lpu_units_list,
            speciality=kwargs.get('speciality'),
            lastName=kwargs.get('lastName')
        )

        for value in query_result:
            result['doctors'].append({
                'uid': value.id,
                'name': {
                    'firstName': value.FirstName,
                    'patronymic': value.PatrName,
                    'lastName': value.LastName,
                },
                'hospitalUid': str(value.lpuId) + '/' + str(value.orgId),
                'speciality': value.speciality,
                'keyEPGU': value.keyEPGU,
            })

            result['hospitals'].append({
                'uid': str(value.lpuId) + '/' + str(value.orgId),
                'name': (unicode(value.lpu_name) + " " + unicode(value.lpu_units_name)).strip(),
                'address': (unicode(value.lpu_address) + " " + unicode(value.lpu_units_address)).strip(),
                # TODO: выяснить используется ли wsdlURL и верно ли указан
                'wsdlURL': 'http://' + SOAP_SERVER_HOST + ':' + str(SOAP_SERVER_PORT) + '/schedule/?wsdl',
                'token': '',
                'key': value.key,
            })

        shutdown_session()
        return result

    def get_list_specialities(self, **kwargs):
        hospital_uid_from = kwargs.get('hospitalUidFrom')
        hospital_uid = kwargs.get('hospitalUid')

        lpu, lpu_list, lpu_units, lpu_units_list = [], [], [], []

        lpu, lpu_units = LPUWorker.parse_hospital_uid(hospital_uid)
        lpu_dw = LPUWorker()
        if lpu:
            lpu_list = lpu_dw.get_list(id=lpu)

        if lpu_units:
            lpu_units_dw = LPU_UnitsWorker()
            lpu_units_list = lpu_units_dw.get_list(uid=lpu_units)

        query_result = self.get_list(
            lpu=lpu_list,
            lpu_units=lpu_units_list,
            speciality=kwargs.get('speciality'),
            lastName=kwargs.get('lastName')
        )
        result = dict()
        result['speciality'] = []
        specialities, lpu_specialities = [], []

        if hospital_uid_from:
            if len(lpu_list):
                proxy_client = Clients.provider(lpu_list[0].protocol, lpu_list[0].proxy.split(';')[0])
            elif len(lpu_units_list):
                proxy_client = Clients.provider(lpu_units_list[0].lpu.protocol, 
                                                lpu_units_list[0].lpu.proxy.split(';')[0])
            if proxy_client:
                lpu_specialities = proxy_client.getSpecialities(hospital_uid_from)

        for value in query_result:
            if value.speciality not in specialities:
                specialities.append(value.speciality)
                speciality = {'speciality': value.speciality,
                              'ticketsPerMonths': -1,
                              'ticketsAvailable': -1,
                              'nameEPGU': "",  # TODO: получать из Speciality, для этого JOIN Personal and Speciality
                              }

                if lpu_specialities:
                    for speciality_quoted in lpu_specialities:
                        if value.speciality == speciality_quoted.speciality:
                            nameEPGU = ""
                            if hasattr(speciality, 'nameEPGU'):
                                nameEPGU = speciality_quoted.nameEPGU
                            speciality = {'speciality': speciality_quoted.speciality,
                                          'ticketsPerMonths': int(speciality_quoted.ticketsPerMonths),
                                          'ticketsAvailable': int(speciality_quoted.ticketsAvailable),
                                          'nameEPGU': nameEPGU,
                                          }

                result['speciality'].append(speciality)

        shutdown_session()
        return result


class UpdateWorker(object):
    """Класс для импорта данных в ИС из КС"""
    session = Session()
    msg = []

    def __del__(self):
        self.session.close()

    def __log(self, msg):
        if msg:
            self.msg.append(msg)

    def __init_database(self):
        """Create tables from models if not exists"""
        from admin.database import init_db
        init_db()

    def __get_proxy_address(self, proxy):
        proxy = proxy.split(';')
        if self.__check_proxy(proxy[0]):
            return proxy[0]

    def __check_proxy(self, proxy):
        if urllib2.urlopen(proxy).getcode() == 200:
            return True
        return False

    def __backup_epgu(self, lpu_id):
#        TODO: Сделать сохранение ключей ЕПГУ для Personal и Speciality через временные таблицы
        pass

    def __restore_epgu(self, lpu_id):
#        TODO: Сделать восстановление ключей ЕПГУ для Personal и Speciality из временных таблиц
        pass

    def __clear_data(self, lpu):
        """Удаляет данные, по указанным ЛПУ"""
        if lpu.lpu_units:
            for lpu_unit in lpu.lpu_units:
                self.session.delete(lpu_unit)
        for unit_parent in self.session.query(UnitsParentForId).filter(UnitsParentForId.LpuId==lpu.id).all():
            self.session.delete(unit_parent)

        self.__backup_epgu(lpu.id)

        for speciality in self.session.query(Speciality).filter(Speciality.lpuId==lpu.id).all():
            self.session.delete(speciality)
        for doctor in self.session.query(Personal).filter(Personal.lpuId==lpu.id).all():
            self.session.delete(doctor)

    def __update_lpu_units(self, lpu):
        """Обновляет информацию о потразделениях"""
        return_units = []
        proxy = self.__get_proxy_address(lpu.proxy)
        if proxy:
            proxy_client = Clients.provider(lpu.protocol, proxy)
            # В Samson КС предполагается, что сначала выбираются ЛПУ Верхнего уровня и они идут в табл lpu_units,
            # а их дети идут в UnitsParentForId
            # Необходимо с этим разобраться
            # т.е. первая выборка должна быть без parent_id (т.к. локальный lpu.id из БД ИС никак не связан с id в КС)
            try:
                units = proxy_client.listHospitals(infis_code=lpu.key)
            except InvalidRequestError, e:
                self.__log('Ошибка: %s' % e)
                print e
                return False
            except TypeError, e:
                print e
                return False
            except Exception, e:
                print e
                self.__log('Ошибка: %s' % e)
            else:
                for unit in units:
                    if not unit.name:
                        continue

                    address = getattr(unit, 'address')
                    if address is None:
                        address = ''
                    self.session.add(LPU_Units(
                        lpuId=lpu.id,
                        orgId=unit.id,
                        name=unicode(unit.name),
                        address=unicode(address)
                    ))
                    return_units.append(unit)
                    try:
                        if hasattr(unit, 'parentId') and unit.parentId:
                            self.session.add(UnitsParentForId(LpuId=lpu.id, OrgId=unit.parentId, ChildId=unit.id))
                        elif hasattr(unit, 'parent_id') and unit.parent_id:
                            self.session.add(UnitsParentForId(LpuId=lpu.id, OrgId=unit.parent_id, ChildId=unit.id))
                    except Exception, e:
                        print e
                        self.__log('Ошибка при добавлении в UnitsParentForId: %s' % e)

                    self.__log('%s: %s' % (unit.id, unit.name))

        return return_units

    def __update_personal(self, lpu, lpu_units):
        """Обновляет информацию о врачах"""
        proxy = self.__get_proxy_address(lpu.proxy)
        result = False

        if proxy and lpu_units:
            proxy_client = Clients.provider(lpu.protocol, proxy)
            for unit in lpu_units:
                if unit.id:
                    try:
                        doctors = proxy_client.listDoctors(hospital_id=unit.id)
                    except InvalidRequestError:
                        self.__log(u'Ошибка при получении списка врачей для %s: %s' % (unit.id, unit.name))
                        continue
                    else:
                        if doctors:
                            result = True
                            for doctor in doctors:
                                if doctor.firstName and doctor.lastName and doctor.patrName:
                                    self.session.add(Personal(
                                        id=doctor.id,
                                        lpuId=lpu.id,
                                        orgId=unit.id,
                                        FirstName=doctor.firstName,
                                        PatrName=doctor.patrName,
                                        LastName=doctor.lastName,
                                        speciality=doctor.speciality,
                                    ))
                                    #TODO: заменить Personal.speciality на FK(Speciality.id)
                                    self.__update_speciality(lpu_id=lpu.id, speciality=doctor.speciality)
                                    self.__log('%s: %s %s %s (%s)' % (doctor.id,
                                                                      doctor.firstName,
                                                                      doctor.lastName,
                                                                      doctor.patrName,
                                                                      doctor.speciality))
        self.__restore_epgu(lpu.id)
        return result

    def __update_speciality(self, **kwargs):
        try:
            self.session.add(Speciality(lpuId=kwargs['lpu_id'], speciality=kwargs['speciality']))
        except InvalidRequestError:
            return False
        else:
            return True

    def __failed_update(self, error=""):
        self.session.rollback()
        # shutdown_session()
        if error:
            self.__log(u'Ошибка обновления: %s' % error)
            self.__log('----------------------------')
        return False

    def __success_update(self):
        self.session.commit()
        # shutdown_session()
        return True

    def update_data(self):
        """Основной метод, который производит вызов внутренних методов обновления данных в БД ИС"""
        # self.session.begin()
        self.__init_database()
        # Update data in tables
        lpu_dw = LPUWorker()
        lpu_list = lpu_dw.get_list()
        if lpu_list:
            for lpu in lpu_list:
                self.__clear_data(lpu)
                self.__log(u'Обновление ЛПУ: %s' % lpu.name)
                try:
                    lpu_units = self.__update_lpu_units(lpu)
                    if lpu_units:
                        if not self.__update_personal(lpu, lpu_units):
                            self.__failed_update(u'Пустой список врачей')
                            continue
                    else:
                        self.__failed_update(u'Не обнаружено подразделений')
                        continue
                    lpu.LastUpdate = time.mktime(datetime.datetime.now().timetuple())
                except WebFault, e:
                    print e
                    self.__failed_update(e)
                except exceptions.UserWarning, e:
                    print e
                    self.__failed_update(e)
                except urllib2.HTTPError, e:
                    print e
                    self.__failed_update(e)
                    continue
                except urllib2.URLError, e:
                    print e
                    self.__failed_update(e)
                    continue
                except Exception, e:
                    print e
                    self.__failed_update(e.message)
                else:
                    self.__success_update()
                    self.__log(u'Обновление прошло успешно!')
                    self.__log('----------------------------')
        return shutdown_session()
