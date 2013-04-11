# -*- coding: utf-8 -*-

import exceptions
import urllib2
import datetime
import time
try:
    import json
except ImportError:
    import simplejson as json

import hl7

from sqlalchemy import or_, and_, func, not_
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.exc import InvalidRequestError
from suds import WebFault

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT
from admin.models import LPU, LPU_Units, UnitsParentForId, Enqueue, Personal, Speciality, Regions, LPU_Specialities
from admin.models import Personal_Specialities, EPGU_Speciality, EPGU_Service_Type, Personal_KeyEPGU
from admin.models import EPGU_Payment_Method, EPGU_Reservation_Type
from service_clients import Clients, ClientEPGU
from is_exceptions import exception_by_code, IS_ConnectionError

from admin.database import Session, shutdown_session


class DataWorker(object):
    """Provider class for current DataWorkers"""
    @classmethod
    def provider(cls, data_type):
        """Вернёт объект для работы с указанным типом данных"""
        data_type = data_type.lower()
        if data_type == 'regions':
            obj = RegionsWorker()
        elif data_type == 'lpu':
            obj = LPUWorker()
        elif data_type == 'lpu_units':
            obj = LPU_UnitsWorker()
        elif data_type == 'enqueue':
            obj = EnqueueWorker()
        elif data_type == 'personal':
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

        query_lpu = self.session.query(*fields)

        if speciality and isinstance(speciality, unicode):
            query_lpu = query_lpu.join(LPU_Specialities).join(Speciality)
            query_lpu = query_lpu.filter(Speciality.name == speciality)

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
                if item.parent:
                    uid += '/' + str(item.parent.OrgId)
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
            _join.extend([LPU, LPU_Specialities, Speciality])

        query_lpu_units = self.session.query(*fields)

        if _join:
            for i in _join:
                query_lpu_units = query_lpu_units.join(i)

        query_lpu_units = query_lpu_units.outerjoin(LPU_Units.lpu)
        # query_lpu_units = query_lpu_units.outerjoin(LPU_Units.parent, aliased=True)
        #.filter(LPU_Units.lpuId == UnitsParentForId.OrgId)

        if len(lpu_units_ids):
            for unit in lpu_units_ids:
                or_list.append(and_(LPU_Units.lpuId == unit[0], LPU_Units.orgId == unit[1]))
            query_lpu_units = query_lpu_units.filter(or_(*or_list))

        if speciality and isinstance(speciality, unicode):
            query_lpu_units = query_lpu_units.filter(Speciality.name == speciality)

        if lpu_id:
            query_lpu_units = query_lpu_units.filter(LPU_Units.lpuId == lpu_id)

        return query_lpu_units.group_by(LPU_Units.id).all()

    def get_by_id(self, id):
        """
        Get LPU_Unit by id
        """
        try:
            result = self.session.query(LPU_Units).filter(LPU_Units.id == int(id)).one()
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

        hospital_uid = kwargs.get('hospitalUid', '')
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
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
                speciality = doctor.speciality[0].name

        hospital_uid_from = kwargs.get('hospitalUidFrom')
        if not hospital_uid_from:
            hospital_uid_from = 0

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
            result = self.session.query(Enqueue).filter(Enqueue.id == int(id)).one()
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
                tickets = [ticket_uid, ]

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
                                'date_time': _ticket_date,
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
            hospitalUid:
                uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            birthday: дата рождения пациента (необязательный)
            doctorUid: id врача, к которому производится запись (обязательный)
            omiPolicyNumber: номер полиса мед. страхования (необязательный)
            sex: пол (необязательный)
            timeslotStart: время записи на приём (обязательный)
            hospitalUidFrom: uid ЛПУ, с которого производится запись (необязательный), используется для записи между ЛПУ

        """
        hospital_uid = kwargs.get('hospitalUid', '')
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        birthday = kwargs.get('birthday')
        doctor_uid = kwargs.get('doctorUid')
        patient = kwargs.get('person')
        sex = kwargs.get('sex')
        omi_policy_number = kwargs.get('omiPolicyNumber')
        if omi_policy_number:
            omi_policy_number = omi_policy_number.strip()
        document_obj = kwargs.get('document')
        document = dict()
        if document_obj:
            if document_obj.client_id:
                document['client_id'] = str(document_obj.client_id)
            if document_obj.policy_type:
                document['policy_type'] = str(document_obj.policy_type)
            if document_obj.document_code:
                document['document_code'] = str(document_obj.document_code)
            if document_obj.series:
                document['serial'] = document_obj.series
            else:
                document['serial'] = ''
            if document_obj.number:
                document['number'] = document_obj.number

        timeslot_start = kwargs.get('timeslotStart', '')

        if hospital_uid and doctor_uid and patient:
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
                'firstName': patient.firstName,
                'lastName': patient.lastName,
                'patronymic': patient.patronymic,
            },
            omiPolicyNumber=omi_policy_number,
            document=document,
            birthday=birthday,
            sex=sex,
            hospitalUid=hospital_uid[1],
            hospitalUidFrom=hospital_uid_from,
            speciality=doctor_info.speciality[0].name.lower(),
            doctorUid=doctor_uid,
            timeslotStart=timeslot_start
        )

        if _enqueue and _enqueue['result'] is True:
            ticket_uid = _enqueue.get('ticketUid').split('/')
            enqueue_id = self.__add_ticket(
                Error=_enqueue.get('error_code'),
                Data=json.dumps({
                    'ticketUID': _enqueue.get('ticketUid'),
                    'timeslotStart': timeslot_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'hospitalUid': kwargs.get('hospitalUid'),
                    'doctorUid': doctor_uid,
                }),
                patient_id=_enqueue.get('patient_id'),
                ticket_id=int(ticket_uid[0]),
            )
            result = {'result': _enqueue.get('result'),
                      'message': exception_by_code(_enqueue.get('error_code')),
                      'ticketUid': _enqueue.get('ticketUid')}

            epgu_dw = EPGUWorker()
            epgu_dw.send_enqueue(
                hospital=lpu_info,
                doctor=doctor_info,
                patient=dict(fio=patient, id=_enqueue.get('patient_id')),
                timeslot=timeslot_start,
                enqueue_id=enqueue_id,
                slot_unique_key=kwargs.get('epgu_slot_id'))
        else:
            enqueue_id = self.__add_ticket(
                Error=_enqueue.get('error_code'),
                Data=json.dumps({
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

    def __delete_epgu_slot(self, hospital, patient_id, ticket_id):
        if not hospital.token or not hospital.keyEPGU:
            return None

        enqueue_record = (self.session.query(Enqueue).
                          filter(and_(Enqueue.patient_id == int(patient_id), Enqueue.ticket_id == int(ticket_id))).
                          one())
        _hospital = dict(auth_token=hospital.token, place_id=hospital.keyEPGU)
        if enqueue_record:
            # TODO: CELERY TASK
            epgu_dw = EPGUWorker()
            epgu_dw.epgu_delete_slot(_hospital, enqueue_record.keyEPGU)

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

    def dequeue(self, **kwargs):
        """Отменяет запись на приём

        Args:
            hospitalUid:
                uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            ticketUid: Идентификатор ранее поданной заявки о записи на приём (обязательный)

        """
        hospital_uid = kwargs.get('hospitalUid', '')
        ticket_uid = kwargs.get('ticketUid', '')
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        if len(hospital_uid) > 1:
            dw = LPUWorker()
            lpu_info = dw.get_by_id(hospital_uid[0])
            proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
        else:
            shutdown_session()
            return dict()

        if ticket_uid:
            ticket_uid = ticket_uid.split('/')
        if len(hospital_uid) > 1:
            ticket_id = ticket_uid[0]
            patient_id = ticket_uid[1]
        else:
            shutdown_session()
            return dict()

        result = proxy_client.dequeue(server_id=lpu_info.key, patient_id=patient_id, ticket_id=ticket_id)
        if result and result['success']:
            self.__delete_epgu_slot(hospital=lpu_info, patient_id=patient_id, ticket_id=ticket_id)

        shutdown_session()
        return result


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
            Personal,
            LPU.name.label('lpu_name'),
            LPU_Units.name.label('lpu_units_name'),
            LPU.address.label('lpu_address'),
            LPU_Units.address.label('lpu_units_address'),
            LPU.phone,
            LPU.key,
        )

        query = query.join(Personal.speciality)
        query = query.outerjoin(LPU)
        query = query.outerjoin(LPU_Units, Personal.orgId == LPU_Units.orgId).filter(Personal.lpuId == LPU_Units.lpuId)

        if speciality:
            query = query.filter(Speciality.name == speciality)
        if lastName:
            query = query.filter(Personal.LastName == lastName)

        query = query.filter(or_(*or_list))
        query = query.order_by(Personal.LastName, Personal.FirstName, Personal.PatrName)
        return query.all()

    def get_doctor(self, **kwargs):
        """Возвращает информацию о враче

        Args:
            doctor_id: id врача  (обязательный)
            lpu_unit: uid ЛПУ или подразделения, список вида: ['17, 0'],
                соответствует ['LPU_ID', 'LPU_Unit_ID'] (необязательный)

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
            query = query.filter(Personal.doctor_id == int(doctor_id))

        return query.one()

    def get_list_doctors(self, **kwargs):
        """Формирует и возвращает список врачей для SOAP

        Args:
            {'searchScope':
                {
                'hospitalUid': uid ЛПУ или подразделения, строка вида: '17/0',
                    соответствует 'LPU_ID/LPU_Unit_ID' (необязательный),
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
            person = value.Personal
            result['doctors'].append({
                'uid': person.doctor_id,
                'name': {
                    'firstName': person.FirstName,
                    'patronymic': person.PatrName,
                    'lastName': person.LastName,
                },
                'hospitalUid': str(person.lpuId) + '/' + str(person.orgId),
                'speciality': person.speciality[0].name,
                'keyEPGU': person.key_epgu.keyEPGU,
            })

            result['hospitals'].append({
                'uid': str(person.lpuId) + '/' + str(person.orgId),
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
            _speciality = value.Personal.speciality[0]
            if _speciality.id not in specialities:
                specialities.append(_speciality.id)
                keyEPGU = None
                if _speciality.epgu_speciality:
                    keyEPGU = _speciality.epgu_speciality.keyEPGU
                speciality = {'speciality': _speciality.name,
                              'ticketsPerMonths': -1,
                              'ticketsAvailable': -1,
                              'nameEPGU': keyEPGU,
                              }

                if lpu_specialities:
                    for speciality_quoted in lpu_specialities:
                        if _speciality.name == speciality_quoted.speciality:
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

    def __init__(self):
        self.msg = []

    def __del__(self):
        self.session.close()

    def __log(self, msg):
        if msg:
            self.msg.append(msg)

    def __init_database(self):
        """Create tables from models if not exists"""
        from admin.database import init_db
        init_db()

    def __get_proxy_address(self, proxy, protocol):
        proxy = proxy.split(';')
        if protocol == 'korus30':
            # не делаем проверку для Thrift, т.к. urllib2.urlopen(proxy) для него не работает
            return proxy[0]
        else:
            if self.__check_proxy(proxy[0]):
                return proxy[0]

    def __check_proxy(self, proxy):
        try:
            if urllib2.urlopen(proxy).getcode() == 200:
                return True
        except urllib2.URLError:
            raise IS_ConnectionError(host=proxy)
        return False

    def __clear_data(self, lpu):
        """Удаляет данные, по указанным ЛПУ"""

        self.session.query(UnitsParentForId).filter(UnitsParentForId.LpuId == lpu.id).delete()

        if lpu.lpu_units:
            [self.session.delete(lpu_unit) for lpu_unit in lpu.lpu_units]

        self.session.query(LPU_Specialities).filter(LPU_Specialities.lpu_id == lpu.id).delete()

        self.session.query(Personal).filter(Personal.lpuId == lpu.id).delete()

        self.session.commit()

    def __update_lpu_units(self, lpu):
        """Обновляет информацию о потразделениях"""
        return_units = []
        proxy = self.__get_proxy_address(lpu.proxy, lpu.protocol)
        if proxy:
            proxy_client = Clients.provider(lpu.protocol, proxy)
            # В Samson КС предполагается, что сначала выбираются ЛПУ Верхнего уровня и они идут в табл lpu_units,
            # а их дети идут в UnitsParentForId
            # Необходимо с этим разобраться
            # т.е. первая выборка должна быть без parent_id (т.к. локальный lpu.id из БД ИС никак не связан с id в КС)
            try:
                units = proxy_client.listHospitals(infis_code=lpu.key)
            except WebFault, e:
                print e
                self.__log(u'Ошибка: %s' % e)
                return False
            except TypeError, e:
                print e
                self.__log(u'Ошибка: %s' % e)
                return False
            except Exception, e:
                print e
                self.__log(u'Ошибка: %s' % e)
                return False
            else:
                for unit in units:
                    if not unit.name:
                        continue

                    address = getattr(unit, 'address')
                    if address is None:
                        address = ''

                    if not getattr(unit, 'parentId', None) and not getattr(unit, 'parent_id', None):
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
                        self.__log(u'Ошибка при добавлении в UnitsParentForId: %s' % e)

                    self.__log(u'%s: %s' % (unit.id, unit.name))

        return return_units

    def __update_personal(self, lpu, lpu_units):
        """Обновляет информацию о врачах"""
        proxy = self.__get_proxy_address(lpu.proxy, lpu.protocol)
        result = False

        if proxy and lpu_units:
            proxy_client = Clients.provider(lpu.protocol, proxy)
            for unit in lpu_units:
                if unit.id:
                    try:
                        doctors = proxy_client.listDoctors(hospital_id=unit.id)
                    except WebFault, e:
                        self.__log(u'Ошибка при получении списка врачей для %s: %s (%s)' % (unit.id, unit.name, e))
                        continue
                    except Exception, e:
                        self.__log(u'Ошибка при получении списка врачей для %s: %s (%s)' % (unit.id, unit.name, e))
                        continue
                    else:
                        if doctors:
                            result = True
                            for doctor in doctors:
                                if doctor.firstName and doctor.lastName and doctor.patrName:
                                    speciality = self.__update_speciality(
                                        lpu_id=lpu.id,
                                        speciality=doctor.speciality.strip()
                                    )
                                    if not speciality:
                                        continue

                                    key_epgu = self.session.query(Personal_KeyEPGU).filter(
                                        Personal_KeyEPGU.doctor_id == doctor.id,
                                        Personal_KeyEPGU.lpuId == lpu.id,
                                        Personal_KeyEPGU.orgId == unit.id
                                    ).first()

                                    if not key_epgu:
                                        key_epgu = Personal_KeyEPGU(
                                            doctor_id=doctor.id,
                                            lpuId=lpu.id,
                                            orgId=unit.id
                                        )
                                        self.session.add(key_epgu)

                                    personal = Personal(
                                        # key_epgu=key_epgu,
                                        doctor_id=doctor.id,
                                        lpuId=lpu.id,
                                        orgId=unit.id,
                                        FirstName=doctor.firstName,
                                        PatrName=doctor.patrName,
                                        LastName=doctor.lastName,
                                        office=getattr(doctor, 'office', None),
                                    )
                                    self.session.add(personal)
                                    self.session.commit()

                                    self.__add_personal_speciality(personal.id, speciality.id)

                                    self.__log(u'%s: %s %s %s (%s)' % (doctor.id,
                                                                      doctor.firstName,
                                                                      doctor.lastName,
                                                                      doctor.patrName,
                                                                      doctor.speciality))
        return result

    def __update_speciality(self, **kwargs):
        speciality = self.session.query(Speciality).filter(Speciality.name == kwargs.get('speciality')).first()
        if not speciality:
            try:
                speciality = Speciality(name=kwargs.get('speciality'))
            except InvalidRequestError, e:
                print e
                self.__failed_update(e)
                return False
            else:
                self.session.add(speciality)
                self.session.commit()
        self.__add_lpu_speciality(speciality_id=speciality.id, lpu_id=kwargs.get('lpu_id'))
        return speciality

    def __add_personal_speciality(self, doctor_id, speciality_id):
        self.session.add(Personal_Specialities(personal_id=doctor_id, speciality_id=speciality_id,))
        self.session.commit()

    def __add_lpu_speciality(self, **kwargs):
        if not self.session.query(LPU_Specialities).filter_by(**kwargs).first():
            try:
                self.session.add(LPU_Specialities(**kwargs))
                self.session.commit()
            except InvalidRequestError, e:
                print e
                self.__failed_update(e)
                return False
        return True

    def __failed_update(self, error=""):
        self.session.rollback()
        # shutdown_session()
        if error:
            self.__log(u'Ошибка обновления: %s' % error)
            self.__log(u'----------------------------')
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
                except IS_ConnectionError, e:
                    print e
                    self.__failed_update(e.message)
                    continue
                except Exception, e:
                    print e
                    self.__failed_update(e.message)
                else:
                    self.__success_update()
                    self.__log(u'Обновление прошло успешно!')
                    self.__log(u'----------------------------')
        return shutdown_session()


class EPGUWorker(object):
    """Класс взаимодействия с ЕПГУ"""
    session = Session()
    proxy_client = ClientEPGU()

    class Struct:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def __init__(self):
        self.msg = []
        self.time_table_period = 90  # TODO: вынести в настройки
        self.schedule_weeks_period = 3  # TODO: вынести в настройки
        self.default_phone = '+79011111111'

    def __del__(self):
        self.session.close()

    def __log(self, msg):
        if msg:
            self.msg.append(msg)

    def __get_token(self):
        lpu_token = self.session.query(LPU.token).filter(and_(LPU.token != '', LPU.token != None)).first()
        if lpu_token:
            return lpu_token.token
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
        lpu_dw = LPUWorker()
        lpu_list = lpu_dw.get_list()
        if lpu_list:
            for lpu in lpu_list:
                if not lpu.token:
                    continue

                epgu_result = self.proxy_client.GetMedicalSpecializations(lpu.token)
                specialities = getattr(epgu_result, 'medical-specialization', None)
                if specialities:
                    epgu_specialities = self.__update_epgu_specialities(specialities=specialities)
                    self.__update_services(specialities=epgu_specialities, lpu_token=lpu.token)
                else:
                    self.__log(getattr(epgu_result, 'error', None))
                self.__log(u'Синхронизированы специальности и услуги по ЛПУ %s' % lpu.name)
                self.__log(u'----------------------------')

    def __update_epgu_specialities(self, specialities):
        result = []
        for speciality in specialities:
            db_speciality = self.session.query(EPGU_Speciality).filter(EPGU_Speciality.name == speciality.name).first()
            if not db_speciality:
                epgu_speciality = EPGU_Speciality(name=speciality.name, keyEPGU=str(speciality.id))
                self.session.add(epgu_speciality)
                result.append(epgu_speciality)
            elif not db_speciality.keyEPGU:
                db_speciality.keyEPGU = speciality.id
                result.append(db_speciality)
        self.session.commit()
        return result

    def __update_services(self, specialities, lpu_token):
        for epgu_speciality in specialities:
            epgu_result = self.proxy_client.GetServiceTypes(auth_token=lpu_token, ms_id=epgu_speciality.keyEPGU)
            epgu_services = getattr(epgu_result, 'service-type', None)
            if epgu_services:
                if not isinstance(epgu_services, list):
                    epgu_services = [epgu_services]
                for service in epgu_services:
                    exists = (self.session.query(EPGU_Service_Type).
                              filter(EPGU_Service_Type.keyEPGU == service.id).count())
                    if not exists:
                        self.session.add(EPGU_Service_Type(name=service.name,
                                                           keyEPGU=str(service.id),
                                                           code=service.code,
                                                           recid=service.recid,
                                                           epgu_speciality_id=epgu_speciality.id))
                self.session.commit()
            else:
                self.__log(getattr(epgu_result, 'error', None))

    def sync_payment_methods(self):
        auth_token = self.__get_token()
        if auth_token:
            epgu_result = self.proxy_client.GetPaymentMethods(auth_token=auth_token)
            payment_methods = getattr(epgu_result, 'payment-method', None)
            if payment_methods:
                for _methods in payment_methods:
                    if not (self.session.query(EPGU_Payment_Method).
                            filter(EPGU_Payment_Method.keyEPGU == _methods.id).
                            count()):
                        self.session.add(EPGU_Payment_Method(name=_methods.name,
                                                             default=(_methods.default == 'true'),
                                                             keyEPGU=str(_methods.id)))
                        self.session.commit()
                self.__log(u'Методы оплаты синхронизированы')
                self.__log(u'----------------------------')
            else:
                self.__log(getattr(epgu_result, 'error', None))

    def sync_reservation_types(self):
        auth_token = self.__get_token()
        if auth_token:
            epgu_result = self.proxy_client.GetReservationTypes(auth_token=auth_token)
            reservation_types = getattr(epgu_result, 'reservation-type', None)
            if reservation_types:
                for _type in reservation_types:
                    if not (self.session.query(EPGU_Reservation_Type).
                            filter(EPGU_Reservation_Type.keyEPGU == _type.id).
                            count()):
                        self.session.add(EPGU_Reservation_Type(name=_type.name, code=_type.code, keyEPGU=str(_type.id)))
                        self.session.commit()
                self.__log(u'Типы резервирования синхронизированы')
                self.__log(u'----------------------------')
            else:
                self.__log(getattr(epgu_result, 'error', None))

    def __get_doctor_by_location(self, location, lpu_id):
        doctor = None
        try:
            fio = location['prefix'].split('-')[0].strip()
            fio = fio.replace('.', ' ')
            fio_list = fio.split()
            lastname = fio_list[0].strip()
            firstname = fio_list[1].strip()
            patrname = fio_list[2].strip()
        except IndexError, e:
            print e
        else:
            doctor = self.session.query(Personal).filter(
                and_(Personal.lpuId == lpu_id,
                     Personal.LastName == lastname,
                     Personal.FirstName.ilike('%s%%' % firstname),
                     Personal.PatrName.ilike('%s%%' % patrname),
                     EPGU_Speciality.keyEPGU == location['epgu_speciality'],
                     )
            ).group_by(Personal.doctor_id).one()
            # TODO: Как быть, если есть тёзка?
        return doctor

    def __update_doctor(self, doctor, data):
        # Заново выбираем, т.к. не работает update commit с текущим пользователем (видимо, Session его забывает)
        doctor = self.session.query(Personal).get(doctor.id)
        for k, v in data.items():
            if k == 'keyEPGU':
                doctor.key_epgu.keyEPGU = v
            if hasattr(doctor, k):
                setattr(doctor, k, v)
        self.session.commit()

    def __delete_location_epgu(self, hospital, location_id):
        self.proxy_client.DeleteEditLocation(hospital, location_id)

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
        return result

    def __get_all_locations(self, hospital):
        result = []
        epgu_result = self.proxy_client.GetLocations(hospital)
        locations = getattr(epgu_result, 'locations', None)
        if locations:
            result.extend(self.__get_location_data(locations))
            num_pages = int(locations.paginate.num_pages)
            if num_pages > 1:
                for page in xrange(2, num_pages + 1):
                    epgu_result = self.proxy_client.GetLocations(hospital=hospital, page=page)
                    locations = getattr(epgu_result, 'locations', None)
                    if locations:
                        result.extend(self.__get_location_data(locations))
                    else:
                        self.__log(getattr(epgu_result, 'error', None))
        else:
            self.__log(getattr(epgu_result, 'error', None))
        return result

    def __get_nearest_monday(self):
        today = datetime.date.today()
        if today.isoweekday() == 1:
            nearest_monday = today
        else:
            nearest_monday = today + datetime.timedelta(days=(7 - today.isoweekday() + 1))
        return nearest_monday

    def __get_reservation_time(self, doctor, date=None):
        reservation_time = None

        enqueue_dw = EnqueueWorker()
        if date is None:
            date = self.__get_nearest_monday()
        params = {
            'hospitalUid': '%s/%s' % (doctor.lpuId, doctor.orgId),
            'doctorUid': doctor.doctor_id,
            'startDate': date,
            'endDate': date + datetime.timedelta(days=1),
        }
        result = enqueue_dw.get_info(**params)
        if result['timeslots']:
            timeslot = result['timeslots'][0]
            reservation_time = (timeslot['finish'] - timeslot['start']).seconds / 60
        return reservation_time

    def __get_service_types(self, doctor, epgu_speciality_id):
        return [doctor.speciality[0].epgu_service_type]
        # return (self.session.query(EPGU_Service_Type).
        #         filter(EPGU_Service_Type.epgu_speciality_id == epgu_speciality_id).
        #         all())

    def __post_location_epgu(self, hospital, doctor):
        if not doctor.speciality or not isinstance(doctor.speciality, list):
            self.__log(
                u'Не найдена специальность у врача %s %s %s (id=%s)' %
                (doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        epgu_speciality = doctor.speciality[0].epgu_speciality
        if not epgu_speciality:
            self.__log(
                u'Нет соответствия специальности %s на ЕПГУ для врача %s %s %s (id=%s)' %
                (doctor.speciality[0].name, doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        try:
            epgu_service_types = self.__get_service_types(doctor, epgu_speciality.id)
        except AttributeError, e:
            print e
            self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
            return None

        params = dict(hospital=hospital)
        payment_method = self.session.query(EPGU_Payment_Method).filter(EPGU_Payment_Method.default == True).one()

        #TODO: reservation_type  = automatic + сделать настройку в админке
        reservation_type = (self.session.query(EPGU_Reservation_Type).
                            filter(EPGU_Reservation_Type.code == 'automatic').
                            one())
        reservation_time = self.__get_reservation_time(doctor)
        if not reservation_time:
            self.__log(u'Не заведено расписание для %s %s %s (id=%s)' %
                       (doctor.LastName, doctor.FirstName, doctor.PatrName, doctor.doctor_id))
            return None

        params['doctor'] = dict(
            prefix=u'%s %s.%s.' % (doctor.LastName, doctor.FirstName[0:1], doctor.PatrName[0:1]),
            medical_specialization_id=epgu_speciality.keyEPGU,
            cabinet_number=doctor.office,
            time_table_period=self.time_table_period,
            reservation_time=reservation_time,
            reserved_time_for_slot=reservation_time,
            reservation_type_id=reservation_type.keyEPGU,
            payment_method_id=payment_method.keyEPGU,
        )
        params['service_types'] = []
        for service_type in epgu_service_types:
            params['service_types'].append(service_type.keyEPGU)
        epgu_result = self.proxy_client.PostLocations(**params)
        location_id = getattr(epgu_result, 'id', None)
        if location_id:
            return location_id
        else:
            self.__log(getattr(epgu_result, 'error', None))
        return None

    def sync_locations(self):
        lpu_dw = LPUWorker()
        lpu_list = lpu_dw.get_list()
        if lpu_list:
            for lpu in lpu_list:
                if not lpu.token:
                    continue

                hospital = dict(auth_token=lpu.token, place_id=lpu.keyEPGU)
                self.__log(u'Синхронизация очередей для %s' % lpu.name)
                locations = self.__get_all_locations(hospital=hospital)
                _exists_locations_id = []
                if locations:
                    for location in locations:
                        _exists_locations_id.append(location['keyEPGU'])
                        doctor = self.__get_doctor_by_location(location, lpu.id)
                        if doctor and doctor.key_epgu.keyEPGU != location['keyEPGU']:
                            self.__update_doctor(doctor, dict(keyEPGU=str(location['keyEPGU'])))
                            self.__log(u'Для %s %s %s получен keyEPGU (%s)' %
                                       (doctor.lastName, doctor.firstName, doctor.patrName, location['keyEPGU']))
                        elif not doctor:
                            self.__delete_location_epgu(hospital, location['keyEPGU'])
                            self.__log(u'Для %s не найден на ЕПГУ, удалена очередь (%s)' %
                                       (location['prefix'].split('-')[0].strip(), location['keyEPGU']))

                add_epgu_doctors = (
                    self.session.query(Personal).
                    options(joinedload(Personal.speciality)).
                    filter(Personal.lpuId == lpu.id).
                    filter(
                        or_(
                            Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU == None),
                            not_(Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU.in_(_exists_locations_id))))).
                    all())
                if add_epgu_doctors:
                    for doctor in add_epgu_doctors:
                        location_id = self.__post_location_epgu(hospital, doctor)
                        if location_id:
                            self.__update_doctor(doctor, dict(keyEPGU=str(location_id)))
                            self.__log(u'Для %s %s %s отправлена очередь, получен keyEPGU (%s)' %
                                       (doctor.LastName, doctor.FirstName, doctor.PatrName, location_id))
                self.__log(u'----------------------------')

    def __link_activate_schedule(self, hospital, doctor, rules):
        epgu_result = self.proxy_client.PutLocationSchedule(
            hospital,
            doctor.key_epgu.keyEPGU,
            rules)
        applied_schedule = getattr(epgu_result, 'applied-schedule', None)
        if applied_schedule:
            applied_rules = getattr(applied_schedule, 'applied-rules', None)
            if applied_rules:
                for applied_rule in getattr(applied_rules, 'applied-rule', []):
                    self.__log(
                        u'Очереди (%s) назначено расписание с %s по %s (%s)' %
                        (getattr(applied_schedule, 'location-id'),
                         getattr(applied_rule, 'start-date'),
                         getattr(applied_rule, 'end-date'),
                         getattr(applied_rule, 'rule-id')))

            epgu_result = self.proxy_client.PutActivateLocation(hospital, doctor.key_epgu.keyEPGU)
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
            except AttributeError, e:
                print e
                self.__log(u'Для специальности %s не указана услуга для выгрузки на ЕПГУ' % doctor.speciality[0].name)
                continue
            fio_list = patient_slot['patient']['fio'].split()
            patient = dict(firstName=fio_list[1], lastName=fio_list[0], id=patient_slot['patient']['id'])
            try:
                patronymic = fio_list[2]
            except IndexError:
                pass
            else:
                patient['patronymic'] = patronymic

            self.epgu_appoint_patient(
                hospital=hospital,
                doctor=dict(location_id=doctor.key_epgu.keyEPGU, epgu_service_type=service_type.keyEPGU),
                patient=patient,
                timeslot=patient_slot['date_time']
            )

    def epgu_appoint_patient(self, hospital, doctor, patient, timeslot):
        slot_unique_key = None
        epgu_result = self.proxy_client.PostReserve(
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
            else:
                self.__log(getattr(epgu_result, 'error', None))
        else:
            self.__log(getattr(epgu_result, 'error', None))
        return slot_unique_key

    def epgu_delete_slot(self, hospital, slot_id):
        epgu_result = self.proxy_client.DeleteSlot(hospital, slot_id)
        _hash = getattr(epgu_result, '_hash', None)
        if not _hash:
            self.__log(getattr(epgu_result, 'error', None))
        return _hash

    def sync_schedule(self):
        lpu_dw = LPUWorker()
        lpu_list = lpu_dw.get_list()
        hospital = dict()
        if lpu_list:
            for lpu in lpu_list:
                hospital[lpu.id] = dict(auth_token=lpu.token, place_id=lpu.keyEPGU)

        today = datetime.datetime.today().date()
        start_date = today - datetime.timedelta(days=(today.isoweekday() - 1))
        end_date = start_date + datetime.timedelta(weeks=self.schedule_weeks_period)
        enqueue_dw = EnqueueWorker()
        epgu_doctors = self.session.query(Personal).filter(
            Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU != None)
        ).all()
        for doctor in epgu_doctors:
            params = {
                'hospitalUid': '%s/%s' % (doctor.lpuId, doctor.orgId),
                'doctorUid': doctor.doctor_id,
                'startDate': start_date,
                'endDate': end_date,
            }
            schedule = enqueue_dw.get_info(**params)
            if schedule:
                doctor_rules = []
                busy_by_patients = []
                days = []
                interval = []
                week_number = 1
                previous_day = None
                for timeslot in schedule['timeslots']:
                    if timeslot['start'].date() >= start_date + datetime.timedelta(weeks=week_number):
                        if days:
                            rule_start = start_date + datetime.timedelta(weeks=(week_number - 1))
                            rule_end = rule_start + datetime.timedelta(days=6)
                            epgu_result = self.proxy_client.PostRules(
                                hospital=hospital[doctor.lpuId],
                                doctor=u'%s %s.%s.' % (doctor.LastName, doctor.FirstName[0:1], doctor.PatrName[0:1]),
                                period='%s-%s' % (rule_start.strftime('%d.%m.%Y'), rule_end.strftime('%d.%m.%Y'), ),
                                days=days)
                            rule = getattr(epgu_result, 'rule', None)
                            if rule:
                                doctor_rules.append(
                                    dict(
                                        id=rule.id,
                                        start=rule_start,
                                        end=rule_end,
                                    ))
                                self.__log(
                                    u'На ЕПГУ отправлено расписание для %s %s %s (%s-%s)' %
                                    (doctor.LastName,
                                     doctor.FirstName,
                                     doctor.PatrName,
                                     rule_start.strftime('%d.%m.%Y'),
                                     rule_end.strftime('%d.%m.%Y')))
                            else:
                                self.__log(getattr(epgu_result, 'error', None))
                            days = []
                        week_number += week_number

                    if previous_day is not None and previous_day != timeslot['start'].date():
                        days.append(dict(date=timeslot['start'], interval=interval))
                        interval = []
                    interval.append(dict(start=timeslot['start'].time().strftime('%H:%M'),
                                         end=timeslot['finish'].time().strftime('%H:%M')))

                    previous_day = timeslot['start'].date()

                    if timeslot['patientId'] and timeslot['patientInfo']:
                        busy_by_patients.append(
                            dict(date_time=timeslot['start'],
                                 patient=dict(id=timeslot['patientId'], fio=timeslot['patientInfo'])
                                 ))

                if doctor_rules:
                    self.__link_activate_schedule(hospital[doctor.lpuId], doctor, doctor_rules)

                if busy_by_patients:
                    self.__appoint_patients(hospital[doctor.lpuId], doctor, busy_by_patients)

    def sync_hospitals(self):
        lpu_list = self.session.query(LPU).filter(or_(~LPU.keyEPGU, LPU.keyEPGU == None))
        if lpu_list:
            for lpu in lpu_list:
                if not lpu.token:
                    self.__log(u'Не заведён токен для ЛПУ %s (id=%i)' % (lpu.name, lpu.id))
                    continue

                epgu_result = self.proxy_client.GetPlace(auth_token=lpu.token)
                place = getattr(epgu_result, 'place', None)
                if place:
                    lpu.keyEPGU = str(place.id)
                    self.__log(getattr(epgu_result, 'error', None))
                else:
                    self.__log(getattr(epgu_result, 'error', None))
            self.session.commit()
            self.__log(u'ЛПУ синхронизированы')
            self.__log(u'----------------------------')

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
                patient = self.Struct(lastName=data['PID'][0][5][0],
                                      firstName=data['PID'][0][5][1],
                                      patronymic=data['PID'][0][5][2])
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
                              slot_id=slot_id,)
        return result

    def __parse_xml(self, message):
        return None

    def __add_by_epgu(self, params):
        try:
            doctor = self.session.query(Personal).filter(
                Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU == params.get('doctor_keyEPGU'))
            ).one()
            hospital = doctor.lpu
        except MultipleResultsFound, e:
            print e
        except NoResultFound, e:
            print e
            return None
        else:
            slot_id = params.get('slot_id')
            if slot_id:
                ticket_exists = self.session.query(Enqueue).filter(Enqueue.keyEPGU == slot_id).count()
                if ticket_exists:
                    self.__log(u'Талончик с keyEPGU=%s уже существует' % slot_id)
                    return False

            enqueue_dw = EnqueueWorker()
            _enqueue = enqueue_dw.enqueue(
                person=params.get('patient'),
                hospitalUid='%i/%i' % (doctor.lpuId, doctor.orgId),
                doctorUid=doctor.doctor_id,
                timeslotStart=params.get('timeslot'),
                epgu_slot_id=slot_id
            )
            if _enqueue and _enqueue['result'] is True:
                return True
            else:
                self.epgu_delete_slot(
                    hospital=dict(auth_token=hospital.token, place_id=hospital.keyEPGU),
                    slot_id=params.get('slot_id'))

    def send_enqueue(self, hospital, doctor, patient, timeslot, enqueue_id, slot_unique_key):
        if not slot_unique_key:
            if not hospital.token or not hospital.keyEPGU:
                return None

            _hospital = dict(auth_token=hospital.token, place_id=hospital.keyEPGU)
            try:
                service_type = doctor.speciality[0].epgu_service_type
            except AttributeError, e:
                print e
                return None
            _doctor = dict(location_id=doctor.key_epgu.keyEPGU, epgu_service_type=service_type.keyEPGU)
            _patient = dict(firstName=patient['fio'].firstName,
                            lastName=patient['fio'].lastName,
                            patronymic=patient['fio'].patronymic,
                            id=patient['id'])

            # TODO: CELERY TASK
            epgu_dw = EPGUWorker()
            slot_unique_key = epgu_dw.epgu_appoint_patient(hospital=_hospital,
                                                           doctor=_doctor,
                                                           patient=_patient,
                                                           timeslot=timeslot)
        if slot_unique_key:
            _enqueue = self.session.query(Enqueue).get(enqueue_id)
            if _enqueue:
                _enqueue.keyEPGU = slot_unique_key
                self.session.commit()

    def __delete_by_epgu(self, params):
        try:
            enqueue = self.session.query(Enqueue).filter(Enqueue.keyEPGU == params.get('slot_id')).one()
        except MultipleResultsFound, e:
            print e
        except NoResultFound, e:
            print e
            return None
        else:
            data = json.loads(enqueue.Data)
            if data['hospitalUid']:
                enqueue_dw = EnqueueWorker()
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
