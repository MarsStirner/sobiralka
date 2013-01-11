# -*- coding: utf-8 -*-

import exceptions
import datetime
import time
import logging
from urlparse import urlparse
from abc import ABCMeta, abstractmethod, abstractproperty
from suds.client import Client
from suds import WebFault
import is_exceptions
import settings

from thrift.transport import TTransport, TSocket, THttpClient
from thrift.protocol import TBinaryProtocol, TProtocol
from core_services.Communications import Client as Thrift_Client
from core_services.ttypes import GetTimeWorkAndStatusParameters, EnqueuePatientParameters
from core_services.ttypes import AddPatientParameters, FindOrgStructureByAdressParameters
from core_services.ttypes import FindPatientParameters, PatientInfo

class Clients(object):
    '''
    Class provider for current Clients
    '''
    @classmethod
    def provider(cls, type, proxy_url):

        logging.basicConfig(level=logging.INFO)
        if settings.DEBUG:
            logging.getLogger('suds.client').setLevel(logging.DEBUG)

        type = type.lower()

        if type in ('samson', 'korus20'):
            obj = ClientKorus20(proxy_url)
        elif type == 'intramed':
            obj = ClientIntramed(proxy_url)
        elif type in ('core', 'korus30'):
            obj = ClientKorus30(proxy_url)
        else:
            obj = None
            raise exceptions.NameError

        return obj


class AbstractClient(object):
    __metaclass__=ABCMeta

    @abstractmethod
    def findOrgStructureByAddress(self):
        pass

    @abstractmethod
    def getScheduleInfo(self):
        pass

    @abstractmethod
    def getPatientQueue(self):
        pass

    @abstractmethod
    def getPatientInfo(self):
        pass

    @abstractmethod
    def getWorkTimeAndStatus(self):
        pass

    @abstractmethod
    def getWorkTimeAndStatus(self):
        pass

    @abstractmethod
    def findPatient(self):
        pass

    @abstractmethod
    def addPatient(self):
        pass

    @abstractmethod
    def enqueue(self):
        pass


class ClientKorus20(AbstractClient):
    def __init__(self, url):
        self.client = Client(url, cache=None)

    def listHospitals(self, **kwargs):
        params['recursive'] = True
        if 'parent_id' in kwargs and kwargs['parent_id']:
            params['parentId'] = kwargs['parent_id']
        try:
            result = self.client.service.getOrgStructures(**params)
        except WebFault, e:
            print e
        else:
            return result['list']
        return None

    def findOrgStructureByAddress(self, **kwargs):
        if (kwargs['serverId']
            and kwargs['number']
#            and kwargs['corpus']
            and kwargs['pointKLADR']
            and kwargs['streetKLADR']
            and kwargs['flat']
            ):
            params = {'serverId': kwargs['serverId'],
                      'number': kwargs['number'],
                      'corpus': kwargs.get('corpus'),
                      'pointKLADR': kwargs['pointKLADR'],
                      'streetKLADR': kwargs['streetKLADR'],
                      'flat': kwargs['flat'],
                      }
            try:
                result = self.client.service.findOrgStructureByAddress(**params)
            except WebFault, e:
                print e
            else:
                return result['list']
        else:
            raise exceptions.AttributeError
        return None

    def getScheduleInfo(self, **kwargs):
        result = []
        if kwargs['start'] and kwargs['end'] and kwargs['doctor_uid']:
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                start = (kwargs['start'].date() + datetime.timedelta(days=i))
                params = {
                    'serverId': kwargs.get('server_id'),
                    'personId': kwargs.get('doctor_uid'),
                    'date': start,
                    'hospitalUidFrom': kwargs.get('hospital_uid_from', '0'),
                    }
                timeslot = self.getWorkTimeAndStatus(**params)
                if timeslot:
                    result.extend(timeslot)
        else:
            raise exceptions.ValueError
        return {'timeslots': result}

    def getWorkTimeAndStatus(self, **kwargs):
        try:
            schedule = self.client.service.getWorkTimeAndStatus(**kwargs)
        except WebFault, e:
            print e
        else:
            if schedule and hasattr(schedule, 'tickets'):
                result = []
                for key, timeslot in enumerate(schedule.tickets):
                    result.append({
                        'start': datetime.datetime.combine(kwargs['date'], timeslot.time),
                        'finish': (
                            datetime.datetime.combine(kwargs['date'], schedule.tickets[key+1].time)
                            if key < (len(schedule.tickets) - 1)
                            else datetime.datetime.combine(kwargs['date'], schedule.endTime)
                            ),
                        'status': 'free' if timeslot.free else 'locked',
                        'office': str(schedule.office),
                        'patientId': timeslot.patientId,
                        'patientInfo': timeslot.patientInfo,
                    })
                return result
        return []

    def getPatientQueue(self, **kwargs):
        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')
        if server_id and patient_id:
            params = {'serverId': server_id, 'patientId': patient_id,}
            try:
                result = self.client.service.getPatientQueue(**params)
            except WebFault, e:
                print e
            else:
                return result['list']
        else:
            raise exceptions.ValueError
        return None

    def getPatientInfo(self, **kwargs):
        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')
        if server_id and patient_id:
            params = {'serverId': server_id, 'patientId': patient_id,}
            try:
                result = self.client.service.getPatientQueue(**params)
            except WebFault, e:
                print e
            else:
                return result['patientInfo']
        else:
            raise exceptions.ValueError
        return None

    def findPatient(self, **kwargs):
        try:
            params = {
#                'serverId': kwargs['serverId'],
                'lastName': kwargs['lastName'],
                'firstName': kwargs['firstName'],
                'patrName': kwargs['patrName'],
                'birthDate': kwargs['birthDate'],
                'omiPolicy': kwargs['omiPolicy'],
                }
        except exceptions.KeyError:
            pass
        else:
            try:
                result = self.client.service.findPatient(**params)
            except WebFault, e:
                print e
            else:
                return result
        return None

    def addPatient(self, **kwargs):
        person = kwargs.get('person')
        if person:
            params = {
#                'serverId': kwargs.get('serverId'),
                'lastName': person.lastName,
                'firstName': person.firstName,
                'patrName': person.patronymic,
#                'omiPolicy': kwargs['omiPolicyNumber'],
                'birthDate': kwargs.get('birthday'),
                }
            try:
                result = self.client.service.addPatient(**params)
            except WebFault, e:
                print e
            else:
                return result
        else:
            raise exceptions.AttributeError
        return {}

    def enqueue(self, **kwargs):
        hospital_uid_from = kwargs.get('hospitalUidFrom')
        person = kwargs.get('person')
        if person is None:
            raise exceptions.AttributeError
            return {}

        patient = self.findPatient(**{
            'serverId': kwargs.get('serverId'),
            'lastName': person.lastName,
            'firstName': person.firstName,
            'patrName': person.patronymic,
            'omiPolicy': kwargs.get('omiPolicyNumber'),
            'birthDate': kwargs.get('birthday'),
        })
        if not patient.success and hospital_uid_from and hospital_uid_from != '0':
            patient = self.addPatient(**kwargs)

        if patient.success and patient.patientId:
            patient_id = patient.patientId
        else:
#            raise exceptions.LookupError
            return {'result': False, 'error_code': patient.message,}

        try:
            date_time = kwargs.get('timeslotStart')
            if not date_time:
                date_time = datetime.datetime.now()
            params = {
                'serverId': kwargs.get('serverId'),
                'patientId': int(patient_id),
                'personId': int(kwargs.get('doctorUid')),
                'date': date_time.date(),
                'time': date_time.time(),
                'note': kwargs.get('E-mail', 'E-mail'),
                'hospitalUidFrom': kwargs.get('hospitalUidFrom'),
                }
        except:
            raise exceptions.ValueError
        else:
            try:
                result = self.client.service.enqueuePatient(**params)
            except WebFault, e:
                print e
            else:
                if result.success:
                    return {
                        'result': True,
                        'error_code': result.message,
                        'ticketUid': str(result.queueId) + '/' + str(patient_id),
                        }
                else:
                    return {
                        'result': False,
                        'error_code': result.message,
                        'ticketUid': '',
                        }
        return None


class ClientIntramed(AbstractClient):
    def __init__(self, url):
        self.url = url

    def listHospitals(self, **kwargs):
        list_client = Client(self.url + 'egov.v3.listPort.CLS?WSDL=1', cache=None)
        try:
            result = list_client.service.listHospitals()
        except WebFault, e:
            print e
        else:
            if 'hospitals' in result:#
            # info_client = Client(self.url + 'egov.v3.infoPort.CLS?WSDL=1', cache=None)
                for key, hospital in result['hospitals']:
                    result['hospitals'][key]['id'] = hospital['uid']
                    result['hospitals'][key]['name'] = hospital['title']
                    result['hospitals'][key]['address'] = ""
#                    hospital_info = info_client.service.getHospitalInfo(hospitalUid=hospital.uid)
                return result['hospitals']
        return None

    def findOrgStructureByAddress(self, **kwargs):
        self.client = Client(self.url + 'egov.v3.listPort.CLS?WSDL=1', cache=None)

        if (kwargs['serverId']
            and kwargs['number']
#            and kwargs['corpus']
            and kwargs['pointKLADR']
            and kwargs['streetKLADR']
            and kwargs['flat']
            ):
            params = {'serverId': kwargs['serverId'],
                      'number': kwargs['number'],
                      'corpus': kwargs['corpus'],
                      'pointKLADR': kwargs['pointKLADR'],
                      'streetKLADR': kwargs['streetKLADR'],
                      'flat': kwargs['flat'],
                      }
        result = []
        if params:
            try:
                result = self.client.service.findOrgStructureByAddress(**params)
                return result['list']
            except WebFault, e:
                print e
        else:
            raise exceptions.ValueError
        return result

    def getScheduleInfo(self, **kwargs):
        self.client = Client(self.url + 'egov.v3.queuePort.CLS?WSDL=1', cache=None)

        result = {}
        result['timeslots'] = []
        if kwargs['start'] and kwargs['end'] and kwargs['doctor_uid'] and kwargs['hospital_uid']:
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                params = {'doctorUid': kwargs['doctor_uid'],
                          'speciality': kwargs['speciality'],
                          'startDate': (kwargs['start'] + i).strftime('%Y-%m-%d'),
                          'hospitalUid': kwargs['hospital_uid'][1],
                          }

                result['timeslots'].extend(self.getWorkTimeAndStatus(**params))
        else:
            raise exceptions.ValueError
        return result

    def getWorkTimeAndStatus(self, **kwargs):
        if self.client is None:
            self.client = Client(self.url + 'egov.v3.queuePort.CLS?WSDL=1', cache=None)
        # TODO: перепроверить параметры для Intramed
        params = {
            'doctorUid': kwargs.get('doctorUid'),
            'speciality': kwargs.get('speciality'),
            'startDate': kwargs.get('startDate'),
            'hospitalUid': kwargs.get('hospitalUid'),
        }

        patient_id = kwargs.get('patientId')

        try:
            schedule = self.client.service.getScheduleInfo(**params)
        except WebFault, e:
            print e
        else:
            result = []
            for key, timeslot in enumerate(schedule.timeslots):
                result.append({
                    'start': timeslot.start,
                    'finish': (schedule.timeslots[key+1].start
                               if key < (len(schedule.timeslots) - 1)
                               else schedule.finish),
                    'status': timeslot.status,
                    'office': '0',
                    })
            return result
        return []

    def getPatientQueue(self, **kwargs):
        self.client = Client(self.url + 'egov.v3.queuePort.CLS?WSDL=1', cache=None)

        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')

        if server_id and patient_id:
            params = {'serverId': server_id, 'patientId': patient_id,}
            try:
                result = self.client.service.getPatientQueue(**params)
            except WebFault, e:
                print e
            else:
                return result['list']
        else:
            raise exceptions.ValueError
        return None

    def getPatientInfo(self, **kwargs):
        self.client = Client(self.url + 'egov.v3.infoPort.CLS?WSDL=1', cache=None)

        if kwargs['serverId'] and kwargs['patientId']:
            params = {'serverId': kwargs['serverId'], 'patientId': kwargs['patientId'],}
            try:
                result = self.client.service.getPatientQueue(**params)
            except WebFault, e:
                print e
            else:
                return result['patientInfo']
        else:
            raise exceptions.ValueError

        return None

    def enqueue(self, **kwargs):
        self.client = Client(self.url + 'egov.v3.queuePort.CLS?WSDL=1', cache=None)
        try:
            params = {
                'person': kwargs.get('person'),
                'omiPolicyNumber': kwargs.get('omiPolicyNumber'),
                'birthday': kwargs.get('birthday'),
                'hospitalUid': kwargs.get('hospitalUid'),
                'speciality': kwargs.get('speciality'),
                'doctorUid': kwargs.get('doctorUid'),
                'timeslotStart': kwargs.get('timeslotStart').strftime('%Y-%m-%d %H:%M:%S') + 'Z',
            }
        except:
            raise exceptions.ValueError
        else:
            try:
                result = self.client.service.enqueue(**params)
            except WebFault, e:
                print e
            else:
                if result.enqueueResult == 'accepted':
                    return {
                        'result': True,
                        'error_code': result.enqueueResult,
                        'ticketUid': result.ticketUid,
                    }
                else:
                    return {'result': False, 'error_code': result.enqueueResult}
        return None


class ClientKorus30(AbstractClient):

    def __init__(self, url):
        self.url = url
        url_parsed = urlparse(self.url)
        host = url_parsed.hostname
        port = url_parsed.port

        socket = TSocket.TSocket(host, port)
        transport = TTransport.TBufferedTransport(socket)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)
        self.client = Thrift_Client(protocol)
        transport.open()

    def listHospitals(self, **kwargs):
        params['recursive'] = True
        if 'parent_id' in kwargs and kwargs['parent_id']:
            params['parent_id'] = kwargs['parent_id']
        try:
            result = self.client.getOrgStructures(**params)
        except WebFault, e:
            print e
        else:
            return result['list']
        return None

    def findOrgStructureByAddress(self, **kwargs):
        if (
            'pointKLADR' in kwargs and
            'streetKLADR' in kwargs and
            'number' in kwargs and
            'flat' in kwargs
        ):
            params = FindOrgStructureByAdressParameters(
#                serverId = kwargs['serverId'],
                number = kwargs['number'],
                corpus = kwargs.get('corpus'),
                pointKLADR = kwargs['pointKLADR'],
                streetKLADR = kwargs['streetKLADR'],
                flat = kwargs['flat'],
            )
            try:
                result = self.client.findOrgStructureByAddress(params)
            except WebFault, e:
                print e
            else:
                return result
        else:
            raise exceptions.AttributeError
        return None

    def getScheduleInfo(self, **kwargs):
        result = []
        if kwargs['start'] and kwargs['end'] and kwargs['doctor_uid']:
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                start = (kwargs['start'].date() + datetime.timedelta(days=i))
                timeslot = self.getWorkTimeAndStatus(
                    serverId = kwargs.get('server_id'),
                   personId =  kwargs.get('doctor_uid'),
                    date = start,
                    hospitalUidFrom = kwargs.get('hospital_uid_from', '0'),
                )
                if timeslot:
                    result.extend(timeslot)
        else:
            raise exceptions.ValueError
        return {'timeslots': result}

    def getPatientQueue(self, **kwargs):
        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')
        if server_id and patient_id:
            params = {'serverId': server_id, 'patientId': patient_id,}
            try:
                result = self.client.getPatientQueue(**params)
            except WebFault, e:
                print e
            else:
                return result['list']
        else:
            raise exceptions.ValueError
        return None

    def getPatientInfo(self, **kwargs):
        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')
        if server_id and patient_id:
            params = PatientInfo(serverId = server_id, patientId = patient_id,)
            try:
                result = self.client.getPatientQueue(params)
            except WebFault, e:
                print e
            else:
                return result['patientInfo']
        else:
            raise exceptions.ValueError
        return None

    def findPatient(self, **kwargs):
        try:
            params = FindPatientParameters(
                lastName = kwargs['lastName'],
                firstName = kwargs['firstName'],
                patrName = kwargs['patrName'],
                birthDate = kwargs['birthDate'],
                omiPolicy = kwargs['omiPolicy'],
            )
        except exceptions.KeyError:
            pass
        else:
            try:
                result = self.client.findPatient(params)
            except WebFault, e:
                print e
            else:
                return result
        return None

    def addPatient(self, **kwargs):
        person = kwargs.get('person')
        if person:
            params = AddPatientParameters(
                lastName = person.lastName,
                firstName = person.firstName,
                patrName = person.patronymic,
                #omiPolicy = kwargs['omiPolicyNumber'],
                birthDate = kwargs.get('birthday'),
            )
            try:
                result = self.client.addPatient(params)
            except WebFault, e:
                print e
            else:
                return result
        else:
            raise exceptions.AttributeError
        return {}

    def getWorkTimeAndStatus(self, **kwargs):
        try:
            date = kwargs.get('date', datetime.datetime.now())
            time_tuple = date.timetuple()
            parameters = GetTimeWorkAndStatusParameters(
                hospitalUidFrom=kwargs.get('hospitalUidFrom'),
                personId=kwargs.get('personId'),
                date=time.mktime(time_tuple)
            )
            schedule = self.client.getWorkTimeAndStatus(parameters)
        except WebFault, e:
            print e
        else:
            if schedule and hasattr(schedule, 'tickets') and schedule.tickets:
                result = []
                for key, timeslot in enumerate(schedule.tickets):
                    result.append({
                        'start': datetime.datetime.combine(kwargs['date'], timeslot.time),
                        'finish': (
                            datetime.datetime.combine(kwargs['date'], schedule.tickets[key+1].time)
                            if key < (len(schedule.tickets) - 1)
                            else datetime.datetime.combine(kwargs['date'], schedule.endTime)
                            ),
                        'status': 'free' if timeslot.free else 'locked',
                        'office': str(schedule.office),
                        'patientId': timeslot.patientId,
                        'patientInfo': timeslot.patientInfo,
                        })
                return result
        return []

    def enqueue(self, **kwargs):
        hospital_uid_from = kwargs.get('hospitalUidFrom')
        person = kwargs.get('person')
        if person is None:
            raise exceptions.AttributeError
            return {}

        patient = self.findPatient(
            serverId = kwargs.get('serverId'),
            lastName = person.lastName,
            firstName = person.firstName,
            patrName = person.patronymic,
            omiPolicy = kwargs.get('omiPolicyNumber'),
            birthDate = kwargs.get('birthday'),
        )
        if not patient.success and hospital_uid_from and hospital_uid_from != '0':
            patient = self.addPatient(**kwargs)

        if patient.success and patient.patientId:
            patient_id = patient.patientId
        else:
        #            raise exceptions.LookupError
            return {'result': False, 'error_code': patient.message,}

        try:
            date_time = kwargs.get('timeslotStart')
            if not date_time:
                date_time = datetime.datetime.now()
            params = EnqueuePatientParameters(
#                serverId = kwargs.get('serverId'),
                patientId = int(patient_id),
                personId = int(kwargs.get('doctorUid')),
                dateTime = time.mktime(date_time.date().timetuple()),
                note = kwargs.get('E-mail', 'E-mail'),
                hospitalUidFrom = kwargs.get('hospitalUidFrom'),
            )
        except:
            raise exceptions.ValueError
        else:
            try:
                result = self.client.enqueuePatient(**params)
            except WebFault, e:
                print e
            else:
                if result.success:
                    return {
                        'result': True,
                        'error_code': result.message,
                        'ticketUid': str(result.queueId) + '/' + str(patient_id),
                        }
                else:
                    return {
                        'result': False,
                        'error_code': result.message,
                        'ticketUid': '',
                        }
        return None