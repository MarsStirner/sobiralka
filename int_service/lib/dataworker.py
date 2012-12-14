# -*- coding: utf-8 -*-

import exceptions
import urllib
import datetime, time
import json
from spyne.model.complex import json
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from suds import WebFault

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT, DB_CONNECT_STRING
from models import LPU, LPU_Units, UnitsParentForId, Enqueue, Personal
from soap_client import Clients
from is_exceptions import exception_by_code

engine = create_engine(DB_CONNECT_STRING)
Session = sessionmaker(bind=engine)

class DataWorker(object):
    '''
    Provider class for current DataWorkers
    '''
    @classmethod
    def provider(cls, type):
        type = type.lower()

        if type == 'lpu':
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


class LPUWorker(object):
    session = Session
    model = LPU

    @classmethod
    def parse_hospital_uid(cls, hospitalUid):
        lpu = []
        lpu_units = []
        if not isinstance(hospitalUid, list):
            hospitalUid = list(hospitalUid)
        for i in hospitalUid:
            tmp_list = i.split('/')
            if tmp_list[1]:
                lpu_units.append(tmp_list)
            else:
                lpu.append(tmp_list[0])

        return (lpu, lpu_units)

    def get_list(self, **kwargs):
        '''
        Get LPU list by parameters
        '''
        if kwargs['id']:
            lpu_ids = kwargs['id']
        if kwargs['speciality']:
            speciality = kwargs['speciality']
        if kwargs['okato_code']:
            okato_code = kwargs['okato_code']

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
            query_lpu = query_lpu.filter(Personal.speciality==speciality)

        if len(lpu_ids):
            query_lpu = query_lpu.filter(LPU.id.in_(lpu_ids))

        if okato_code:
            query_lpu = query_lpu.filter(LPU.OKATO.like('%' + okato_code + '%'))

        return query_lpu.all()

    def get_lpu_by_address(self, **kwargs):
        '''
        Get LPU list by address parameters
        '''
        if (kwargs['parsedAddress']['kladrCode']
            and kwargs['parsedAddress']['block']
            and kwargs['parsedAddress']['flat']
#            and kwargs['parsedAddress']['house']['building']
            and kwargs['parsedAddress']['house']['number']
            ):
            # Prepare search parameters
            streetKLADR = kwargs['parsedAddress']['kladrCode']
            pointKLADR = kwargs['parsedAddress']['kladrCode'][0:5].ljust(15, '0')
        else:
            return []

        result = []

        if kwargs['lpu_list']:
            used_proxy = []
            # Use LPU proxy for searching by Soap
            for lpu in kwargs['lpu_list']:
                proxy = lpu.proxy.split(';')
                if proxy[0] and proxy[0] not in used_proxy:
                    used_proxy.append(proxy[0])
                    proxy_client = Clients.provider(lpu.protocol, proxy[0])
                    result.append(proxy_client.findOrgStructureByAddress({
                        'serverId': lpu.key,
                        'number': kwargs['parsedAddress']['house']['number'],
                        'corpus': kwargs['parsedAddress']['house']['building'],
                        'pointKLADR': pointKLADR,
                        'streetKLADR': streetKLADR,
                        'flat': kwargs['parsedAddress']['house']['flat'],
                    }))

        if result:
            result = self._get_lpu_ids(result)

        return result

    def _get_lpu_ids(self, lpu_list):
        '''
        Get ids and OrgIds by lpu data list
        lpu_list contains info from `findOrgStructureByAddress` remote method
        '''
        for key, item in lpu_list:
            query = (self.session.query(UnitsParentForId.OrgId, LPU.id)
                     .filter(UnitsParentForId.LpuId==LPU.id)
                     .filter(LPU.key==item['serverId'])
                     .filter(UnitsParentForId.ChildId==int(item['orgStructureId'])))
            try:
                lpu_ids = query.one()
            except MultipleResultsFound, e:
                print e
            else:
                lpu_list[key]['id'] = lpu_ids.id
                lpu_list[key]['OrgId'] = lpu_ids.OrgId

        return lpu_list

    def get_list_hospitals(self, **kwargs):
        '''
        Get list of LPUs and LPU_Units
        '''
        result = {'hospitals':[]}
        lpu = []
        lpu_units = []

        if kwargs['hospitalUid']:
            lpu, lpu_units = LPUWorker.parse_hospital_uid(kwargs['hospitalUid'])

        speciality = ""
        okato_code = ""
        if kwargs['speciality']:
            speciality = kwargs['speciality']
        if kwargs['okato_code']:
            okato_code = kwargs['okato_code']

        lpu_list = self.get_list(id=lpu, speciality=speciality, okato_code=okato_code)
        # Append LPUs to result
        for item in lpu_list:
            result['hospitals'].append({
                'uid': item.id + '/0',
                'title': item.name,
                'phone': item.phone,
                'address': item.address,
                'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + SOAP_SERVER_PORT + '/schedule/?wsdl',
                'token': item.token,
                'key': item.key,
                }
            )

        if not okato_code:
            units_dw = LPU_UnitsWorker()
            lpu_units_list = units_dw.get_list(uid=lpu_units, speciality=speciality)
            # Append LPU_Units to result
            for item in lpu_units_list:
                if item.parentId:
                    uid = item.id + '/' + item.parentId
                else:
                    uid = item.id +'/0'

                result['hospitals'].append({
                    'uid': uid,
                    'title': item.name,
                    'phone': item.phone,
                    'address': item.address,
                    # TODO: выяснить используется ли wsdlURL и верно ли указан
                    'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + SOAP_SERVER_PORT + '/schedule/?wsdl',
                    'token': item.token,
                    'key': item.key,
                    }
                )
        return result

    def get_info(self, **kwargs):
        '''
        Get info about LPU/LPUs and its Units
        '''
        lpu, lpu_units = [], []
        result = {}
        if kwargs['hospitalUid']:
            lpu, lpu_units = self.parse_hospital_uid(kwargs['hospitalUid'])

        lpu_units_dw = LPU_UnitsWorker()

        for lpu_item in self.get_list(id=lpu):
            units = []
            for lpu_units_item in lpu_units_dw.get_list(uid=lpu_units, lpu_id=lpu_item.id):
                units.append({
                    'id': lpu_units_item.id,
                    'title': lpu_units_item.name,
                    'address': lpu_units_item.address,
                    'phone': lpu_item.phone,
                    'schedule': lpu_item.schedule,
                })

            result['info'].append({
                'uid': lpu_item.id + '/0',
                'title': lpu_item.name,
                'type': lpu_item.type,
                'phone': lpu_item.phone,
                'email': lpu_item.email,
                'siteURL': '',
                'schedule': lpu_item.schedule,
                'buildings': units,
            })

        return result

    def get_by_id(self, id):
        '''
        Get LPU by id and check if proxy url is available
        '''
        try:
            result = self.session.query(LPU).filter(LPU.id==int(id)).one()
        except NoResultFound, e:
            print e
        else:
            result.proxy = result.proxy.split(';')[0]
            if urllib.urlopen(result.proxy).getcode() == 200:
                return result
            else:
                raise WebFault

        return None


class LPU_UnitsWorker(object):
    session = Session
    model = LPU_Units

    def get_list(self, **kwargs):
        '''
        Get LPU_Units list by parameters
        '''
        if kwargs['uid']:
            lpu_units_ids = kwargs['uid']
        if kwargs['speciality']:
            speciality = kwargs['speciality']
        if kwargs['lpu_id']:
            lpu_id = kwargs['lpu_id']

        # Prepare query for getting LPU_Units
        fields = [LPU_Units.id, LPU_Units.lpuId, LPU_Units.name, LPU_Units.address,
                  LPU.phone, LPU.token, LPU.key, UnitsParentForId.lpuId.label('parentId')]
        filter = []
        _join = []
        _outerjoin = [LPU, UnitsParentForId]

        if speciality and isinstance(speciality, unicode):
            fields.append(Personal.speciality)
            _join.append(Personal)

        query_lpu_units = self.session.query(*fields)

        if _join:
            for i in _join:
                query_lpu_units = query_lpu_units.join(i)

        if _outerjoin:
            for i in _outerjoin:
                query_lpu_units = query_lpu_units.outerjoin(i)

        if len(lpu_units_ids):
            for unit in lpu_units_ids:
                or_list.append((LPU_Units.lpuId==unit[0], LPU_Units.id==unit[1]))
            query_lpu_units = query_lpu_units.filter(or_(or_list))

        if speciality and isinstance(speciality, unicode):
            query_lpu_units = query_lpu_units.filter(Personal.speciality==speciality)

        if lpu_id:
            query_lpu_units = query_lpu_units.filter(LPU_Units.lpuId==lpu_id)

        return query_lpu_units.all()


    def get_by_id(self, id):
        '''
        Get LPU_Unit by id
        '''
        try:
            result = self.session.query(LPU_Units).filter(LPU_Units.id==int(id)).one()
        except NoResultFound, e:
            print e
        else:
            return result

        return None


class EnqueueWorker(object):
    session = Session
    model = Enqueue
    SCHEDULE_DAYS_DELTA = 14

    def get_info(self, **kwargs):
        result = {}

        if kwargs['hospitalUid']:
            hospital_uid = kwargs['hospitalUid'].split('/')
            if len(hospital_uid)==2:
                lpu_dw = LPUWorker()
                lpu = lpu_dw.get_by_id(hospital_uid[0])
            else:
                raise exceptions.ValueError
                return {}
        else:
            raise exceptions.ValueError
            return {}

        if kwargs['doctorUid']:
            doctor_uid = kwargs['doctor_uid']
        else:
            raise exceptions.ValueError
            return {}

        speciality = ""
        if kwargs['speciality']:
            speciality = kwargs['speciality']

        hospital_uid_from = 0
        if kwargs['hospitalUidFrom']:
            hospital_uid_from = kwargs['hospitalUidFrom']

        start, end = '', ''
        if kwargs['start']:
            start = kwargs['start']
        if kwargs['end']:
            end = kwargs['end']

        start, end = self.__get_dates_period(start, end)

        proxy_client = Clients.provider(lpu.protocol, lpu.proxy.split(';')[0])
        result = proxy_client.getScheduleInfo(
            hospital_uid=hospital_uid,
            doctor_uid = doctor_uid,
            start=start,
            end=end,
            speciality = speciality,
            hospital_uid_from = hospital_uid_from,
            server_id = lpu.key
        )

        return result

    def __get_dates_period(self, start='', end=''):
        if not start:
#            start = time.mktime(datetime.datetime.today().timetuple())
            start = datetime.datetime.today()

        if not end:
#            end = time.mktime((datetime.datetime.today() + datetime.timedelta(self.SCHEDULE_DAYS_DELTA)).timetuple())
            end = (datetime.datetime.today() + datetime.timedelta(days=self.SCHEDULE_DAYS_DELTA))

        return (start, end)

    def __get_tickets_ge_id(self, id, hospital_uid=None):
        tickets = []
        for item in self.session.query().filter(
            Enqueue.DataType=='0',
            Enqueue.id>id,
            Enqueue.Error=='100 ok',
            Enqueue.status==0
        ):
            data = json.load(item.Data)
            if hospital_uid and hospital_uid==data['hospitalUid'] or hospital_uid is None:
                tickets.append({
                    'id': item.id,
                    'data': data,
                    'error': item.error,
                })
        return tickets

    def get_by_id(self, id):
        '''
        Get Ticket by id and check
        '''
        try:
            result = self.session.query(Enqueue).filter(Enqueue.id==int(id)).one()
        except NoResultFound, e:
            print e
        else:
            return result

        return None

    def get_ticket_status(self, **kwargs):
        '''
        Get tickets' status
        '''
        result = {}
        if kwargs['hospitalUid'] and kwargs['ticketUid']:
            hospital_uid = kwargs['hospitalUid'].split('/')
            if len(hospital_uid)==2:
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
                raise exceptions.ValueError
                return {}
        else:
            raise exceptions.ValueError
            return {}

        if kwargs['lastUid']:
            tickets = self.__get_tickets_ge_id(kwargs['lastUid'], kwargs['hospitalUid'])
        else:
            if isinstance(kwargs['ticketUid'], list):
                tickets = kwargs['ticketUid']
            else:
                tickets = list(kwargs['ticketUid'])

        doctor_dw = PersonalWorker()
        if tickets:
            for ticket in tickets:
                # TODO: разнести по отдельным методам
                if isinstance(ticket, dict):
                    # Working on case where kwargs['lastUid']

                    # For low code dependence get current hospital_uid
                    _hospital_uid = ticket.data.hospital_uid.split('/')

                    doctor = doctor_dw.get_doctor(lpu_unit=_hospital_uid, doctor_id=ticket.data.doctorUid)
                    result['ticketInfo'].append({
                        'id': ticket.id,
                        'ticketUid': ticket.data.ticketUid,
                        'hospitalUid': ticket.data.hospitalUid,
                        'doctorUid': ticket.data.doctorUid,
                        'doctor': {
                            'firstName': doctor.firstName if doctor.firstName else '',
                            'patronymic': doctor.patronymic if doctor.patronymic else '',
                            'lastName': doctor.lastName if doctor.lastName else '',
                        },
                        'person': {
                            'firstName': '',
                            'patronymic': '',
                            'lastName': '',
                        },
                        'status': 'forbidden',
                        'timeslotStart': datetime.datetime.strptime(ticket.data.timeslotStart, '%Y-%m-%dT%H:%M:%S'),
                        'comment': str(exception_by_code(ticket.Error)),
                        'location': lpu_name + " " + lpu_address,
                    })

                else:

                    ticket_uid, patient_id = ticket.split('/')

                    queue_info = proxy_client.getPatientQueue({'serverId': server_id, 'patientId': patient_id})
                    patient_info = proxy_client.getPatientQueue({'serverId': server_id, 'patientId': patient_id})

                    for ticket_info in queue_info:
                        if ticket_info.queueId == ticket_uid:
                            doctor = doctor_dw.get_doctor(lpu_unit=hospital_uid, doctor_id=ticket_info.personId)

                            if ticket_info.enqueuePersonId:
                                # TODO: проверить действительно ли возвращаемый enqueuePersonId - это office
                                office = ticket_info.enqueuePersonId
                            else:
                                work_times = proxy_client.getWorkTimeAndStatus({
                                    'serverId': server_id,
                                    'personId': ticket_info.personId,
                                    'date': ticket_info.enqueueDate,
                                })
                                if work_time:
                                    office = work_time[0].office

                            _ticket_date = datetime.datetime.strptime(
                                ticket_info.date + ticket_info.time, '%Y-%m-%d %H:%M:%S'
                            )

                            document = self.__get_ticket_print({
                                'name': lpu_name,
                                'address': lpu_address,
                                'fio': patient_info.lastName + ' ' +
                                       patient_info.firstName[0:1] + '. ' +
                                       patient_info.patrName[0:1] + '. ',
                                'person': (doctor.lastName + ' ' if doctor.lastName else '' +
                                           doctor.firstName + ' ' if doctor.firstName else '' +
                                           doctor.patronymic + ' ' if doctor.patronymic else ''
                                    ),
                                'date_time':_ticket_date,
                                'office': office,
                            })

                            result['ticketInfo'].append({
                                'id': '',
                                'ticketUid': ticket,
                                'hospitalUid': hospital_uid,
                                'doctorUid': ticket_info.personId,
                                'doctor': {
                                    'firstName': doctor.firstName if doctor.firstName else '',
                                    'patronymic': doctor.patronymic if doctor.patronymic else '',
                                    'lastName': doctor.lastName if doctor.lastName else '',
                                    },
                                'person': {
                                    'firstName': patient_info.firstName,
                                    'patronymic': patient_info.patrName,
                                    'lastName': patient_info.lastName,
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

        return result

    def __get_ticket_print(self, **kwargs):
        '''
        Return generated pdf for ticket print
        '''
        # TODO: выяснить используется ли pdf в принципе. В эл.регестратуре он никак не используется
        # TODO: pdf creator based on Flask templates and xhtml2pdf
        return ""

    def enqueue(self, **kwargs):
        '''
        Запись на приём к врачу
        '''
        if (kwargs['hospitalUid'] and
            kwargs['birthday'] and
            kwargs['doctorUid'] and
            kwargs['person'] and
            kwargs['omiPolicyNumber']
            ):
            hospital_uid = kwargs['hospitalUid'].split('/')
            if len(hospital_uid)==2:
                dw = LPUWorker()
                lpu_info = dw.get_by_id(hospital_uid[0])
                proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
            else:
                raise exceptions.ValueError
                return {}
        else:
            raise exceptions.ValueError
            return {}

        result = {}

        person_dw = PersonalWorker()
        doctor_info = person_dw.get_doctor(lpu_unit = hospital_uid, doctor_id = kwargs['doctorUid'])

        hospital_uid_from = kwargs['hospitalUidFrom'] if kwargs['hospitalUidFrom'] else 0

        if not doctor_info:
            raise exceptions.LookupError
            return {}

        _enqueue = proxy_client.enqueue({
            'serverId': lpu_info['key'],
            'person': {
                'firstName': kwargs['person']['firstName'],
                'lastName': kwargs['person']['lastName'],
                'patronymic': kwargs['person']['patronymic'],
            },
            'omiPolicyNumber': kwargs['omiPolicyNumber'],
            'birthday': kwargs['birthday'].split('T')[0],
            'hospitalUid': hospital_uid[1],
            'hospitalUidFrom': hospital_uid_from,
            'speciality': doctor_info.speciality,
            'doctorUid': kwargs['doctorUid'],
            'timeslotStart': kwargs['timeslotStart'],
        })

        if _enqueue and _enqueue.result == True:
            self.__add_ticket({
                'Error': _enqueue.message,
                'Data': json.dumps({
                    'ticketUID':_enqueue.ticketUid,
                    'timeslotStart':kwargs['timeslotStart'],
                    'timeslhospitalUidotStart':kwargs['hospitalUid'],
                    'doctorUid':kwargs['doctorUid'],
                }),
            })
            result = {'result': exception_by_code(_enqueue.message), 'ticketUid': _enqueue.ticketUid}
        else:
            enqueue_id = self.__add_ticket({
                'Error': _enqueue.message,
                'Data': json.dumps({
                    'ticketUID':_enqueue.ticketUid,
                    'timeslotStart':kwargs['timeslotStart'],
                    'timeslhospitalUidotStart':kwargs['hospitalUid'],
                    'doctorUid':kwargs['doctorUid'],
                    }),
                })
            result = {'result': exception_by_code(_enqueue.message), 'ticketUid': 'e' + enqueue_id}

        return result

    def __add_ticket(self, **kwargs):
        try:
            enqueue = Enqueue(**kwargs)
        except exceptions.ValueError, e:
            print e
        else:
            self.session.add(enqueue)
            self.session.commit()
            return enqueue.id
        return None


class PersonalWorker(object):
    session = Session
    model = Personal

    def get_list(self, **kwargs):
        '''
        Get Doctors list by lpu & lpu_units
        '''
        if kwargs['lpu']:
            lpu = kwargs['lpu']
        if kwargs['lpu_units']:
            lpu_units = kwargs['lpu_units']

        result = {}
        query = self.session.query(
            Personal.FirstName,
            Personal.PatrName,
            Personal.LastName,
            Personal.speciality,
            Personal.id,
            Personal.personId,
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
        or_list = []
        if lpu:
            for item in lpu:
                or_list.append((Personal.lpuId==item.id,))
        if lpu_units:
            for item in lpu:
                or_list.append((Personal.lpuId==item.lpuId, Personal.orgId==item.id))

        query = query.outerjoin(LPU).outerjoin(LPU_Units)

        for value in query.filter(or_(or_list)).all():
            result['doctors'].append({
                'uid': value.personId,
                'name': {
                    'firstName': value.FirstName,
                    'patronymic': value.PatrName,
                    'lastName': value.LastName,
                },
                'hospitalUid': value.lpuId + '/' + value.orgId,
                'speciality': value.speciality,
                'keyEPGU': value.keyEPGU,
            })

            result['hospitals'].append({
                'uid': value.lpuId + '/' + value.orgId,
                'title': (value.lpu_name + " " + value.lpu_units_name).trim(),
                'address': (value.lpu_address + " " + value.lpu_units_address).trim(),
                # TODO: выяснить используется ли wsdlURL и верно ли указан
                'wsdlURL': 'http://' + SOAP_SERVER_HOST + ':' + SOAP_SERVER_PORT + '/schedule/?wsdl',
                'token': '',
                'key': value.key,
            })

        return result

    def get_doctor(self, **kwargs):
        '''
        Get doctor by parameters
        '''
        if kwargs['lpu_unit']:
            lpu_unit = kwargs['lpu_unit']
        if kwargs['doctor_id']:
            doctor_id = kwargs['doctor_id']

        query = self.session.query(Personal)

        if lpu_unit:
            if lpu_unit[1]:
                query.filter(Personal.lpuId==lpu_unit[0], Personal.orgId==lpu_unit[1])
            else:
                query.filter(Personal.lpuId==lpu_unit[0])
        if person_id:
            query.filter(Personal.personId==doctor_id)

        return query.one()

    def get_list_doctors(self, **kwargs):
        '''
        Get doctors list by parameters
        '''
        if kwargs['searchScope']['hospitalUid']:
            lpu, lpu_units = LPU_Worker.parse_hospital_uid(kwargs['searchScope']['hospitalUid'])

        lpu_dw = LPUWorker()
        lpu_list = lpu_dw.get_list(id=lpu)

        if kwargs['searchScope']['address']:
            # TODO: уточнить используется ли поиск по адресу
            lpu_list = lpu_dw.get_lpu_by_address(kwargs['searchScope']['address'], lpu_list)

        lpu_units_dw = LPU_UnitsWorker()
        lpu_units_list = lpu_units_dw.get_list(uid=lpu_units)

        return self.get_list(lpu=lpu_list, lpu_units=lpu_units_list)


class UpdateWorker(object):
    pass