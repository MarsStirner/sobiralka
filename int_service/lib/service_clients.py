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
    """Class provider for current Clients"""
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
    def enqueue(self):
        pass


class ClientKorus20(AbstractClient):
    """Класс клиента для взаимодействия со старой КС"""
    def __init__(self, url):
        """
        Args:
            url: URL-адрес WSDL старой КС

        """
        self.client = Client(url, cache=None)

    def listHospitals(self, **kwargs):
        """Получает список подразделений

        Args:
            parent_id: id ЛПУ, для которого необходимо получить подразделения (необязательный)
            infis_code: infis_code ЛПУ, для которого необходимо получить подразделения (необязательный)

        Returns:
            Массив найденных подразделений. Пример:
            [OrgStructureInfo: (OrgStructureInfo){
               id = 108
               parentId = None
               name = "Главные специалисты МЗ и СР ПО"
               address = None
               sexFilter = None
               ageFilter =
                  (AgeFilter){
                     _id = "ref1"
                     from =
                        (AgeSpec){
                           unit = "y"
                           count = 18
                        }
                     to =
                        (AgeSpec){
                           unit = "y"
                           count = 130
                        }
                  }
             },]

        """
        params = {}
        params['recursive'] = True
        if 'parent_id' in kwargs and kwargs['parent_id']:
            params['parentId'] = kwargs['parent_id']
        if 'infis_code' in kwargs and kwargs['infis_code']:
            params['serverId'] = kwargs['infis_code']
        try:
            result = self.client.service.getOrgStructures(**params)
        except WebFault, e:
            print e
        else:
            return result
        return None

    def listDoctors(self, **kwargs):
        """Получает список врачей

        Args:
            hospital_id: id ЛПУ, для которого необходимо получить список врачей (необязательный)

        Returns:
            Массив найденных врачей. Пример:
            [PersonInfo: (PersonInfo){
               orgStructureId = 108
               id = 428
               code = "222"
               lastName = "Бартош"
               firstName = "Леонид"
               patrName = "Федорович"
               office = "607"
               post = "Главный терапевт"
               speciality = "Терапевт (лечебное дело, педиатрия)"
               specialityRegionalCode = "27"
               specialityOKSOCode = None
               sexFilter = None
               ageFilter = None
             },]

        """
        params = {}
        params['recursive'] = True
        if 'hospital_id' in kwargs and kwargs['hospital_id']:
            params['orgStructureId'] = kwargs['hospital_id']
        try:
            result = self.client.service.getPersonnel(**params)
        except WebFault, e:
            print e
        else:
            return result
        return None

    def findOrgStructureByAddress(self, **kwargs):
        """Получает подразделение по адресу пациента

        Args:
            serverId: infisCode ЛПУ
            pointKLADR: код населённого пункта по КЛАДР
            streetKLADR: код улицы по КЛАДР
            number: номер дома
            corpus: корпус дома (необязательный)
            flat: квартира

        """
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
        """Формирует и возвращает информацию о расписании приёма врача

        Args:
            start: дата начала расписания (обязательный)
            end: дата окончания расписания (обязательный)
            doctor_uid: id врача (обязательный)
            hospital_uid_from: id ЛПУ, из которого производится запрос (необязательный)

        """
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
            raise exceptions.AttributeError
        return {'timeslots': result}

    def getWorkTimeAndStatus(self, **kwargs):
        """Возвращает расписание врача на определенную дату

        Args:
            personId: id врача (обязательный)
            date: дата, на которую запрашивается расписание (обязательный)
            hospitalUidFrom: id ЛПУ, из которого производится запрос (необязательный)

        """
        try:
            schedule = self.client.service.getWorkTimeAndStatus(**kwargs)
        except WebFault, e:
            print e
        else:
            if schedule and hasattr(schedule, 'tickets'):
                result = []
                for key, timeslot in enumerate(schedule.tickets):
                    result.append({
                        'start': datetime.datetime.combine(kwargs.get('date'), timeslot.time),
                        'finish': (
                            datetime.datetime.combine(kwargs.get('date'), schedule.tickets[key+1].time)
                            if key < (len(schedule.tickets) - 1)
                            else datetime.datetime.combine(kwargs.get('date'), schedule.endTime)
                            ),
                        'status': 'free' if timeslot.free else 'locked',
                        'office': str(schedule.office),
                        'patientId': timeslot.patientId,
                        'patientInfo': timeslot.patientInfo,
                    })
                return result
        return []

    def getPatientQueue(self, **kwargs):
        """Возвращает информацию о записях пациента

        Args:
            serverId: infis код ЛПУ (обязательный)
            patientId: id пациента (обязательный)

        """
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
        """Возвращает информацию о пациенте

        Args:
             serverId: infis код ЛПУ (обязательный)
             patientId: id пациента (обязательный)

        """
        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')
        if server_id and patient_id:
            params = {'serverId': server_id, 'patientId': patient_id,}
            try:
                result = self.client.service.getPatientInfo(**params)
            except WebFault, e:
                print e
            else:
                return result['patientInfo']
        else:
            raise exceptions.ValueError
        return None

    def findPatient(self, **kwargs):
        """Получает id пациента по параметрам

        Args:
            lastName: фамилия (обязательный)
            firstName: имя (обязательный)
            patrName: отчество (обязательный)
            birthDate: дата рождения (обязательный)
            omiPolicy: номер полиса ОМС (обязательный)

        """
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
        """Добавление пациента в БД ЛПУ

        Args:
            person: словарь с данными о пациенте (обязательный):
                {'lastName': фамилия
                'firstName': имя
                'patronymic': отчество
                }
            birthDate: дата рождения (необязательный)

        """
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
        """Записывает пациента на приём

        Args:
            person: словарь с данными о пациенте (обязательный):
                {'lastName': фамилия
                'firstName': имя
                'patronymic': отчество
                }
            hospitalUidFrom: id ЛПУ, из которого производится запись (необязательный)

        """
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
    """Класс клиента для работы с Интрамед"""
    def __init__(self, url):
        self.url = url

    def listHospitals(self, **kwargs):
        """Получает список ЛПУ"""
        list_client = Client(self.url + 'egov.v3.listPort.CLS?WSDL=1', cache=None)
#        info_client = Client(self.url + 'egov.v3.infoPort.CLS?WSDL=1', cache=None)
        try:
            result = list_client.service.listHospitals()
        except WebFault, e:
            print e
        else:
            try:
                hospitals = []
                for hospital in result['hospitals']:
#                    hospital_info = info_client.service.getHospitalInfo(hospitalUid=hospital.uid)
                    hospitals.append({
                        'id': int(hospital.uid),
                        'name': unicode(hospital.title),
                        'address': unicode(hospital.address),
                        })
            except exceptions.AttributeError:
                pass
            else:
                return hospitals
        return None

    def listDoctors(self, **kwargs):
        """Получает список врачей

        Args:
            hospital_id: id ЛПУ, для которого необходимо получить список врачей (необязательный)

        """
        doctors = []
        list_client = Client(self.url + 'egov.v3.listPort.CLS?WSDL=1', cache=None)
        if 'hospital_id' and kwargs['hospital_id']:
            params = {'searchScope': {'hospitalUid': str(kwargs['hospital_id'])}}
        try:
            result = list_client.service.listDoctors(**params)
        except WebFault, e:
            print e
        else:
            if 'doctors' in result:
                for doctor in result.doctors:
                    doctors.append({
                        'id': int(doctor.uid),
                        'firstName': doctor.name.firstName,
                        'lastName': doctor.name.lastName,
                        'patrName': doctor.name.patronymic,
                        'speciality': doctor.speciality,
                    })
        return doctors

    def findOrgStructureByAddress(self, **kwargs):
        """Получает подразделение по адресу пациента

        Args:
            serverId: infisCode ЛПУ
            pointKLADR: код населённого пункта по КЛАДР
            streetKLADR: код улицы по КЛАДР
            number: номер дома
            corpus: корпус дома (необязательный)
            flat: квартира

        """
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
        """Формирует и возвращает информацию о расписании приёма врача

        Args:
            start: дата начала расписания (обязательный)
            end: дата окончания расписания (обязательный)
            doctor_uid: id врача (обязательный)
            hospital_uid_from: id ЛПУ, из которого производится запрос (необязательный)

        """
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
        """Возвращает расписание врача на определенную дату

        Args:
            doctorUid: id врача (обязательный)
            startDate: дата, на которую запрашивается расписание (обязательный)
            speciality: дата, на которую запрашивается расписание (обязательный)
            hospitalUid: id ЛПУ (необязательный)

        """
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
        """Возвращает информацию о записях пациента

        Args:
            serverId: infis код ЛПУ (обязательный)
            patientId: id пациента (обязательный)

        """
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
        """Возвращает информацию о пациенте

        Args:
             serverId: infis код ЛПУ (обязательный)
             patientId: id пациента (обязательный)

        """
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
        """Записывает пациента на приём

        Args:
            person: словарь с данными о пациенте (обязательный):
                {'lastName': фамилия
                'firstName': имя
                'patronymic': отчество
                }
            hospitalUidFrom: id ЛПУ, из которого производится запись (необязательный)

        """
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
    """Класс клиента для взаимодействия с КС в ядре"""

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
        """Получает список подразделений

        Args:
            parent_id: id ЛПУ, для которого необходимо получить подразделения (необязательный)
            infis_code: infis_code ЛПУ, для которого необходимо получить подразделения (необязательный)

        """
        params = {}
        params['recursive'] = True
        if 'parent_id' in kwargs and kwargs['parent_id']:
            params['parent_id'] = kwargs['parent_id']
        if 'infis_code' in kwargs and kwargs['infis_code']:
            params['infisCode'] = str(kwargs['infis_code'])
        try:
            result = self.client.getOrgStructures(**params)
        except WebFault, e:
            print e
        else:
            return result['list']
        return None

    def listDoctors(self, **kwargs):
        """Получает список врачей

        Args:
            hospital_id: id ЛПУ, для которого необходимо получить список врачей (необязательный)

        """
        params = {}
        params['recursive'] = True
        if 'hospital_id' in kwargs and kwargs['hospital_id']:
            params['orgStructureId'] = kwargs['hospital_id']
        try:
            result = self.client.getPersonnel(params)
        except WebFault, e:
            print e
        else:
            return result['list']
        return None

    def findOrgStructureByAddress(self, **kwargs):
        """Получает подразделение по адресу пациента

        Args:
            serverId: infisCode ЛПУ
            pointKLADR: код населённого пункта по КЛАДР
            streetKLADR: код улицы по КЛАДР
            number: номер дома
            corpus: корпус дома (необязательный)
            flat: квартира

        """
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
        """Формирует и возвращает информацию о расписании приёма врача

        Args:
            start: дата начала расписания (обязательный)
            end: дата окончания расписания (обязательный)
            doctor_uid: id врача (обязательный)
            hospital_uid_from: id ЛПУ, из которого производится запрос (необязательный)

        """
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
        """Возвращает информацию о записях пациента

        Args:
            serverId: infis код ЛПУ (обязательный)
            patientId: id пациента (обязательный)

        """
        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')
        if server_id and patient_id:
            params = PatientInfo(infisCode = server_id, patientId = patient_id,)
            try:
                result = self.client.getPatientQueue(params)
            except WebFault, e:
                print e
            else:
                return result['list']
        else:
            raise exceptions.ValueError
        return None

    def getPatientInfo(self, **kwargs):
        """Возвращает информацию о пациенте

        Args:
             serverId: infis код ЛПУ (обязательный)
             patientId: id пациента (обязательный)

        """
        server_id = kwargs.get('serverId')
        patient_id = kwargs.get('patientId')
        if server_id and patient_id:
            params = PatientInfo(infisCode = server_id, patientId = patient_id,)
            try:
                result = self.client.getPatientInfo(params)
            except WebFault, e:
                print e
            else:
                return result['patientInfo']
        else:
            raise exceptions.ValueError
        return None

    def findPatient(self, **kwargs):
        """Получает id пациента по параметрам

        Args:
            lastName: фамилия (обязательный)
            firstName: имя (обязательный)
            patrName: отчество (обязательный)
            birthDate: дата рождения (обязательный)
            omiPolicy: номер полиса ОМС (обязательный)

        """
        try:
            params = FindPatientParameters(
                lastName=kwargs.get('lastName'),
                firstName=kwargs.get('firstName'),
                patrName=kwargs.get('patrName'),
                birthDate=kwargs.get('birthDate'),
                omiPolicy=kwargs.get('omiPolicy'),
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
        """Добавление пациента в БД ЛПУ

        Args:
            person: словарь с данными о пациенте (обязательный):
                {'lastName': фамилия
                'firstName': имя
                'patronymic': отчество
                }
            birthDate: дата рождения (необязательный)

        """
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
        """Возвращает расписание врача на определенную дату

        Args:
            personId: id врача (обязательный)
            date: дата, на которую запрашивается расписание (обязательный)
            hospitalUidFrom: id ЛПУ, из которого производится запрос (необязательный)

        """
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
        """Записывает пациента на приём

        Args:
            person: словарь с данными о пациенте (обязательный):
                {'lastName': фамилия
                'firstName': имя
                'patronymic': отчество
                }
            hospitalUidFrom: id ЛПУ, из которого производится запись (необязательный)

        """
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