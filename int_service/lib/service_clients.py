# -*- coding: utf-8 -*-

import exceptions
import datetime
import calendar
import base64
import logging
from urlparse import urlparse
from abc import ABCMeta, abstractmethod, abstractproperty
from suds.client import Client
#from suds.plugin import MessagePlugin
#from suds.cache import DocumentCache
from suds import WebFault
import is_exceptions
import settings
import urllib2
import socket

from jinja2 import Environment, PackageLoader

from thrift.transport import TTransport, TSocket, THttpClient
from thrift.protocol import TBinaryProtocol, TProtocol
from core_services.Communications import Client as Thrift_Client, TApplicationException
from core_services.ttypes import GetTimeWorkAndStatusParameters, EnqueuePatientParameters
from core_services.ttypes import AddPatientParameters, FindOrgStructureByAddressParameters
from core_services.ttypes import FindPatientParameters, FindMultiplePatientsParameters, PatientInfo
from core_services.ttypes import SQLException, NotFoundException, TException
from core_services.ttypes import AnotherPolicyException, InvalidDocumentException, InvalidPersonalInfoException
from core_services.ttypes import FindPatientByPolicyAndDocumentParameters, NotUniqueException
from core_services.ttypes import ChangePolicyParameters, Policy, PolicyTypeNotFoundException

from tfoms_service import TFOMSClient, AnswerCodes, logger

# From rbPolicyType.id to rbPolicyType.code (с сайта приходит id в Korus30 необходимо передавать code),
# а Korus20 работает с id
# TODO: необходимо избавиться от этого костыля!
# TODO: для начала изменить на сайте, потом перенести в Korus20 обратное сопоставление, как только старые КС выпиляться
# костыль будет не нужен
_policy_types_mapping = {
    1: dict(core=2, tfoms=2),
    2: dict(core=1, tfoms=1),
    3: dict(core=4, tfoms=4),
    4: dict(core='cmiCommonElectron', tfoms=3)
}

_tfoms_to_core_policy_type = {
    1: 1,
    2: 2,
    3: 'cmiCommonElectron',
    4: 4,
}

class Clients(object):
    """Class provider for current Clients"""
    @classmethod
    def provider(cls, client_type, proxy_url):
        logging.basicConfig(level=logging.ERROR)
        if settings.DEBUG:
            logging.getLogger('suds.client').setLevel(logging.ERROR)
            logging.getLogger('Thrift_Client').setLevel(logging.DEBUG)
        else:
            logging.getLogger('suds.client').setLevel(logging.CRITICAL)
            logging.getLogger('Thrift_Client').setLevel(logging.CRITICAL)

        client_type = client_type.lower()
        if client_type in ('samson', 'korus20'):
            obj = ClientKorus20(proxy_url)
        elif client_type == 'intramed':
            obj = ClientIntramed(proxy_url)
        elif client_type in ('core', 'korus30'):
            obj = ClientKorus30(proxy_url)
        else:
            obj = None
            raise exceptions.NameError
        return obj


class AbstractClient(object):
    __metaclass__ = ABCMeta

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
        if settings.DEBUG:
            self.client = Client(url, cache=None)
        else:
            self.client = Client(url)

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
        params = dict()
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
        params = dict()
        params['recursive'] = True
        if 'hospital_id' in kwargs and kwargs['hospital_id']:
            params['orgStructureId'] = kwargs['hospital_id']
        try:
            result = self.client.service.getPersonnel(**params)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            return result
        return None

    def getSpecialities(self, hospital_uid_from):
        try:
            result = self.client.service.getSpecialities(hospitalUidFrom=hospital_uid_from)
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
            server_id = kwargs.get('server_id')
            doctor_uid = kwargs.get('doctor_uid')
            hospital_uid_from = kwargs.get('hospital_uid_from', '0')
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                start = (kwargs['start'] + datetime.timedelta(days=i))
                params = {
                    'serverId': server_id,
                    'personId': doctor_uid,
                    'date': start,
                    'hospitalUidFrom': hospital_uid_from,
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
                    if timeslot.available:
                        status = 'free'
                    elif timeslot.patientId:
                        status = 'locked'
                    else:
                        status = 'disabled'
                    result.append({
                        'start': datetime.datetime.combine(kwargs.get('date'), timeslot.time),
                        'finish': (
                            datetime.datetime.combine(kwargs.get('date'), schedule.tickets[key + 1].time)
                            if key < (len(schedule.tickets) - 1)
                            else datetime.datetime.combine(kwargs.get('date'), schedule.endTime)
                        ),
                        'status': status,
                        'office': schedule.office,
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
            params = {'serverId': server_id, 'patientId': patient_id, }
            try:
                result = self.client.service.getPatientInfo(**params)
            except WebFault, e:
                print e
            else:
                return result['patientInfo']
        else:
            raise exceptions.ValueError
        return None

    def __sex_parse(self, code):
        if code == 1:
            name = u'М'
        elif code == 2:
            name = u'Ж'
        else:
            name = ''
        return name

    def findPatients(self, **kwargs):
        """Получает id пациентов по параметрам

        Args:
            lastName: фамилия (обязательный)
            firstName: имя (обязательный)
            patrName: отчество (обязательный)

        """
        try:
            document = kwargs.get('document')
            if document and 'serial' in document:
                document['series'] = document['serial']
                del document['serial']
            params = {
                #                'serverId': kwargs['serverId'],
                'lastName': kwargs['lastName'],
                'firstName': kwargs['firstName'],
                'patrName': kwargs['patrName'],
            }
            birthDate = kwargs.get('birthDate')
            sex = kwargs.get('sex')
            document = kwargs.get('document')

            if birthDate:
                params['birthDate'] = birthDate
            if sex:
                params['sex'] = sex
            if document:
                params['document'] = document

            omiPolicy = kwargs.get('omiPolicy')
            if omiPolicy:
                params['omiPolicy'] = omiPolicy  # для совместимости со старой версией сайта и киоска
        except exceptions.KeyError:
            pass
        else:
            try:
                result = self.client.service.findPatients(**params)
            except WebFault, e:
                print e
            else:
                return result
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
            document = kwargs.get('document')
            if document and 'serial' in document:
                document['series'] = document['serial']
                del document['serial']

            params = {
                #                'serverId': kwargs['serverId'],
                'lastName': kwargs['lastName'],
                'firstName': kwargs['firstName'],
                'patrName': kwargs['patrName'],
            }
            birthDate = kwargs.get('birthDate')
            sex = kwargs.get('sex')
            document = kwargs.get('document')

            if birthDate:
                params['birthDate'] = birthDate
            if sex:
                params['sex'] = sex
            if document:
                params['document'] = document

            omiPolicy = kwargs.get('omiPolicy')
            if omiPolicy:
                params.update({'omiPolicy': omiPolicy}) # для совместимости со старой версией сайта и киоска
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
                'lastName': person.get('lastName'),
                'firstName': person.get('firstName'),
                'patrName': person.get('patronymic'),
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
            timeslotStart: Желаемое время начала приёма (обязательный)
            hospitalUidFrom: id ЛПУ, из которого производится запись (необязательный)

        """
        hospital_uid_from = kwargs.get('hospitalUidFrom')
        person = kwargs.get('person')
        if person is None:
            raise exceptions.AttributeError
            return {}

        document = kwargs.get('document')
        birthDate = kwargs.get('birthday')
        if document and birthDate:
            patient = self.findPatient(
                serverId=kwargs.get('serverId'),
                lastName=person.get('lastName'),
                firstName=person.get('firstName'),
                patrName=person.get('patronymic'),
                omiPolicy=kwargs.get('omiPolicyNumber'),
                document=document,
                sex=kwargs.get('sex', 0),
                birthDate=birthDate,
            )

            if not patient.success and hospital_uid_from and hospital_uid_from != '0':
                # TODO: запись с ЕПГУ тоже должна проходить? НЕТ! Без доп. идентификации нельзя.
                patient = self.addPatient(**kwargs)
        else:
            patient = self.findPatient(
                serverId=kwargs.get('serverId'),
                lastName=person.get('lastName'),
                firstName=person.get('firstName'),
                patrName=person.get('patronymic'),
                birthDate=birthDate
            )
            exception_code = int(patient.message.split()[0])

            if exception_code == int(is_exceptions.IS_PatientNotRegistered()):
                if not patient.success and hospital_uid_from and hospital_uid_from != '0':
                # TODO: запись с ЕПГУ тоже должна проходить?
                    patient = self.addPatient(**kwargs)

        if patient.success and patient.patientId:
            patient_id = patient.patientId
        else:
#            raise exceptions.LookupError
            return {'result': False, 'error_code': patient.message, }

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
                'note': kwargs.get('email', 'E-mail'),
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
                        'patient_id': patient_id,
                    }
                else:
                    return {
                        'result': False,
                        'error_code': result.message,
                        'ticketUid': '',
                    }
        return None

    def dequeue(self, server_id, patient_id, ticket_id):
        if server_id and patient_id and ticket_id:
            try:
                result = self.client.service.dequeuePatient(serverId=server_id, patientId=patient_id, queueId=ticket_id)
            except WebFault, e:
                print e
            else:
                return dict(
                    success=result.success,
                    comment=u'Запись на приём отменена.' if result.success else u'Ошибка отмены записи на приём.')
        else:
            raise exceptions.ValueError
        return None


class ClientIntramed(AbstractClient):
    """Класс клиента для работы с Интрамед"""

    class Struct:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

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
                    params = {
                        'id': int(hospital.uid),
                        'name': unicode(hospital.title),
                        'address': unicode(hospital.address),
                    }
                    hospitals.append(self.Struct(**params))
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
        params = dict()
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
                    params = {
                        'id': int(doctor.uid),
                        'firstName': doctor.name.firstName,
                        'lastName': doctor.name.lastName,
                        'patrName': doctor.name.patronymic,
                        'speciality': doctor.speciality,
                    }
                    doctors.append(self.Struct(**params))
        return doctors

    def getSpecialities(self, hospital_uid_from):
        try:
            result = self.client.service.getSpecialities({'hospitalUidFrom': hospital_uid_from})
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
        self.client = Client(self.url + 'egov.v3.listPort.CLS?WSDL=1', cache=None)
        params = dict()
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
            hospital_uid: id ЛПУ (обязательный)

        """
        self.client = Client(self.url + 'egov.v3.queuePort.CLS?WSDL=1', cache=None)

        result = dict()
        result['timeslots'] = []
        if kwargs['start'] and kwargs['end'] and kwargs['doctor_uid'] and kwargs['hospital_uid']:
            params = {'doctorUid': kwargs['doctor_uid'],
                      'speciality': kwargs['speciality'],
                      'startDate': kwargs['start'],
                      'endDate': kwargs['end'],
                      'hospitalUid': kwargs['hospital_uid'][1],
                      }
            result['timeslots'].extend(self.getWorkTimeAndStatus(**params))
#            for i in xrange((kwargs['end'] - kwargs['start']).days):
#                start = (kwargs['start'].date() + datetime.timedelta(days=i))
#                params = {'doctorUid': kwargs['doctor_uid'],
#                          'speciality': kwargs['speciality'],
#                          'startDate': start.strftime('%Y-%m-%d'),
#                          'hospitalUid': kwargs['hospital_uid'][1],
#                          }
#
#                result['timeslots'].extend(self.getWorkTimeAndStatus(**params))
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
        params = {
            'doctorUid': kwargs.get('doctorUid'),
            'speciality': kwargs.get('speciality'),
            'startDate': kwargs.get('startDate'),
            'endDate': kwargs.get('endDate'),
            'hospitalUid': kwargs.get('hospitalUid'),
        }

        try:
            schedule = self.client.service.getScheduleInfo(**params)
        except WebFault, e:
            print e
        else:
            if schedule:
                result = []
                count_timeslots = len(schedule)
                for key, timeslot in enumerate(schedule):
                    result.append({
                        'start': timeslot.start,
                        'finish': timeslot.finish,
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
            params = {'serverId': kwargs['serverId'], 'patientId': kwargs['patientId'], }
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
            person = kwargs.get('person')
            params = {
                'person': person,
                'omiPolicyNumber': kwargs.get('omiPolicyNumber'),
                'birthday': kwargs.get('birthday'),
                'hospitalUid': kwargs.get('hospitalUid'),
                'speciality': kwargs.get('speciality'),
                'doctorUid': kwargs.get('doctorUid'),
                'timeslotStart': kwargs.get('timeslotStart'),
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
                        'patient_id': result.ticketUid,  # TODO: понять не передаётся ли из Интрамеда patient_id
                    }
                else:
                    return {'result': False, 'error_code': result.enqueueResult}
        return None

    def dequeue(self, server_id, patient_id, ticket_id):
        pass


class ClientKorus30(AbstractClient):
    """Класс клиента для взаимодействия с КС в ядре"""

    class Struct:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

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

    def __unicode_result(self, data):
        # DEPRECATED
        # TODO: убрать метод, после проверки
        for element in data:
            for attr, value in element.__dict__.iteritems():
                if isinstance(value, basestring):
                    setattr(element, attr, value.strip().decode('utf8'))
        return data

    def listHospitals(self, **kwargs):
        """Получает список подразделений

        Args:
            parent_id: id ЛПУ, для которого необходимо получить подразделения (необязательный)
            infis_code: infis_code ЛПУ, для которого необходимо получить подразделения (необязательный)

        """
        params = dict()
        params['recursive'] = True
        params['parent_id'] = kwargs.get('parent_id', 0)
        params['infisCode'] = str(kwargs.get('infis_code', ""))
        try:
            result = self.client.getOrgStructures(**params)
        except NotFoundException, e:
            print e.error_msg
        except WebFault, e:
            print e
        else:
            #return self.__unicode_result(result)
            return result
        return None

    def listDoctors(self, **kwargs):
        """Получает список врачей

        Args:
            hospital_id: id ЛПУ, для которого необходимо получить список врачей (необязательный)

        """
        params = dict()
        params['recursive'] = True
        params['orgStructureId'] = kwargs.get('hospital_id')
        params['infisCode'] = str(kwargs.get('infis_code', ""))
        try:
            result = self.client.getPersonnel(**params)
        except SQLException, e:
            print e.error_msg
        except NotFoundException, e:
            print e.error_msg
        except WebFault, e:
            print e
        else:
            #return self.__unicode_result(result)
            return result
        return None

    def getSpecialities(self, hospital_uid_from):
        try:
            result = self.client.getSpecialities(hospital_uid_from)
        except WebFault, e:
            print e
        else:
            #return self.__unicode_result(result)
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
        if (
            'pointKLADR' in kwargs and
            'streetKLADR' in kwargs and
            'number' in kwargs and
            'flat' in kwargs
        ):
            params = FindOrgStructureByAddressParameters(
#                serverId = kwargs['serverId'],
                number=kwargs['number'],
                corpus=kwargs.get('corpus'),
                pointKLADR=kwargs['pointKLADR'],
                streetKLADR=kwargs['streetKLADR'],
                flat=kwargs['flat'],
            )
            try:
                result = self.client.findOrgStructureByAddress(params)
            except WebFault, e:
                print e
            except NotFoundException:
                return []
            else:
                #return self.__unicode_result(result)
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
            server_id = kwargs.get('server_id')
            doctor_uid = kwargs.get('doctor_uid')
            hospital_uid_from = kwargs.get('hospital_uid_from')
            if not hospital_uid_from:
                hospital_uid_from = ''
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                start = (kwargs['start'] + datetime.timedelta(days=i))
                try:
                    timeslot = self.getWorkTimeAndStatus(
                        serverId=server_id,
                        personId=doctor_uid,
                        date=start,
                        hospitalUidFrom=hospital_uid_from,
                    )
                except NotFoundException, e:
                    print e.error_msg
                    continue
                else:
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
            except SQLException, e:
                print e.error_msg
            except WebFault, e:
                print e
            else:
                #return self.__unicode_result(result['list'])
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
            params = PatientInfo(infisCode=server_id, patientId=patient_id)
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
            document: документ пациента, словарь (обязательный)
            sex: пол пациента (обязательный)

        """
        document = kwargs.get('document')
        if not document:
            document = dict()
        params = {
            'lastName': kwargs.get('lastName'),
            'firstName': kwargs.get('firstName'),
            'patrName': kwargs.get('patrName'),
            'birthDate': kwargs.get('birthDate'),
            'document': document,
            'sex': kwargs.get('sex'),
        }

        try:
            result = self.client.findPatient(FindPatientParameters(**params))
        except NotFoundException, e:
            raise e
        except TException, e:
            raise e
        except WebFault, e:
            print e
        else:
            return result
        return None

    def findPatients(self, **kwargs):
        """Получает id пациента по параметрам

        Args:
            lastName: фамилия (обязательный)
            firstName: имя (обязательный)
            patrName: отчество (обязательный)
            birthDate: дата рождения (необязательный)
            document: документ пациента, словарь (необязательный)
            sex: пол пациента (необязательный)

        """
        params = {
            'lastName': kwargs.get('lastName'),
            'firstName': kwargs.get('firstName'),
            'patrName': kwargs.get('patrName'),
        }

        birthDate = kwargs.get('birthDate')
        document = kwargs.get('document')
        sex = kwargs.get('sex')

        if birthDate:
            params['birthDate'] = birthDate
        if document:
            params['document'] = document
        if sex:
            params['sex'] = sex

        try:
            result = self.client.findPatients(FindMultiplePatientsParameters(**params))
        except NotFoundException, e:
            raise e
        except TException, e:
            raise e
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
                'patrName': отчество
                }
            birthDate: дата рождения (необязательный)

        """
        params = AddPatientParameters(
            lastName=kwargs.get('lastName'),
            firstName=kwargs.get('firstName'),
            patrName=kwargs.get('patrName'),
            #omiPolicy = kwargs['omiPolicyNumber'],
            birthDate=kwargs.get('birthDate'),
            sex=int(kwargs.get('sex', 0)),
        )
        try:
            result = self.client.addPatient(params)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            return result
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
                date=calendar.timegm(time_tuple) * 1000
            )
            schedule = self.client.getWorkTimeAndStatus(parameters)
        except WebFault, e:
            print e
        except NotFoundException, e:
            print e.error_msg
        else:
            if schedule and hasattr(schedule, 'tickets') and schedule.tickets:
                result = []
                date_time_by_date = datetime.datetime(kwargs['date'].year, kwargs['date'].month, kwargs['date'].day)
                for key, timeslot in enumerate(schedule.tickets):
                    if key < (len(schedule.tickets) - 1):
                        finish = date_time_by_date + datetime.timedelta(seconds=schedule.tickets[key+1].time/1000)
                    else:
                        finish = date_time_by_date + datetime.timedelta(seconds=schedule.endTime/1000)

                    if timeslot.free and timeslot.available:
                        status = 'free'
                    elif timeslot.free:
                        status = 'disabled'
                    else:
                        status = 'locked'

                    result.append({
                        'start': date_time_by_date + datetime.timedelta(seconds=timeslot.time/1000),
                        'finish': finish,
                        'status': status,
                        'office': schedule.office,
                        'patientId': timeslot.patientId if hasattr(timeslot, 'patientId') else None,
                        'patientInfo': (
                            timeslot.patientInfo
                            if hasattr(timeslot, 'patientInfo') and timeslot.patientInfo
                            else None
                        ),
                    })
                return result
        return []

    def __prepare_tfoms_params(self, data):
        """Подготавливает словарь параметров для осуществления поиска в ТФОМС"""
        person = data.get('person')
        params = {'lastName': person.get('lastName'),
                  'firstName': person.get('firstName'),
                  'patrName': person.get('patronymic')}

        document = data.get('document')
        birthDate = data.get('birthday')

        if document:
            params.update(document)
        if birthDate:
            params['birthDate'] = birthDate

        return params

    def __check_by_tfoms(self, patient):
        """Проверка пациента в ТФОМС"""
        tfoms_client = TFOMSClient(settings.TFOMS_SERVICE_HOST,
                                   settings.TFOMS_SERVICE_PORT,
                                   settings.TFOMS_SERVICE_USER,
                                   settings.TFOMS_SERVICE_PASSWORD)
        if tfoms_client.is_available and tfoms_client.is_logined:
            return tfoms_client.search_patient(patient)
        else:
            return None

    def __prepare_patient_params(self, data):
        """Подготовка словаря параметров пациента для поиска в ЛПУ"""
        person = data.get('person')
        if person is None:
            raise exceptions.AttributeError

        patient_params = {'serverId': data.get('serverId'),
                          'lastName': person.get('lastName').title(),
                          'firstName': person.get('firstName').title(),
                          'patrName': person.get('patronymic').title(),
                          'sex': data.get('sex', 0)}

        omiPolicy = data.get('omiPolicyNumber', '')
        document = data.get('document')
        birthDate = data.get('birthday')

        if omiPolicy:
            patient_params['omiPolicy'] = omiPolicy
        if document:
            if 'serial' in document:
                document['serial'] = document['serial']
            patient_params['document'] = document
        if birthDate:
            patient_params['birthDate'] = calendar.timegm(birthDate.timetuple()) * 1000
        return patient_params

    def __get_patient_by_lpu(self, data):
        """Поиск пациента в БД ЛПУ. Добавление его при записи между ЛПУ"""

        patient_params = self.__prepare_patient_params(data)
        hospital_uid_from = data.get('hospitalUidFrom')
        patient = self.Struct(success=False, patientId=None, message=None)
        try:
            if 'birthDate' in patient_params and 'document' in patient_params:
                patient = self.findPatient(**patient_params)
            else:
                patients = self.findPatients(**patient_params)
                if len(patients) > 1:
                    patient.message = int(is_exceptions.IS_FoundMultiplePatients())
                    #return {'result': False, 'error_code': int(is_exceptions.IS_FoundMultiplePatients()), }
                    return patient
                elif len(patients) == 0:
                    if hospital_uid_from == '0':
                        patient.message = int(is_exceptions.IS_PatientNotRegistered())
                        #return {'result': False, 'error_code': int(is_exceptions.IS_PatientNotRegistered()), }
                        return patient
                else:
                    patient = self.Struct(success=True, patientId=patients[0].id)
        except NotFoundException, e:
            print e
            if hospital_uid_from == '0':
                patient.message = e.error_msg
                #return {'result': False, 'error_code': e.error_msg.decode('utf-8')}
            return patient
        except TException, e:
            print e
            patient.message = e.message
            #return {'result': False, 'error_code': e.message}
            return patient
        except Exception, e:
            print e
            patient.message = e
            #return {'result': False, 'error_code': e}
            return patient

        if not patient.success and hospital_uid_from and hospital_uid_from != '0':
            patient = self.addPatient(**patient_params)
        return patient

    def __update_policy(self, patient_id, data):
        policy_params = dict()
        if data['policySerial']:
            policy_params['serial'] = data['policySerial']
        policy_params['number'] = data['policyNumber']
        policy_params['typeCode'] = data['policyTypeCode']
        policy_params['insurerInfisCode'] = data['policyInsurerInfisCode']
        policy = Policy(**policy_params)
        update_policy_params = ChangePolicyParameters(patientId=patient_id,
                                                      policy=policy)
        return self.client.changePatientPolicy(update_policy_params)

    def __prepare_tfoms_data(self, tfoms_data):
        """"Mapping данных, полученных из ТФОМС в словарь для поиска в БД ЛПУ"""
        params = dict()
        params['lastName'] = tfoms_data.get('lastname', '').title()
        params['firstName'] = tfoms_data.get('firstName', '').title()
        params['patrName'] = tfoms_data.get('midname', '').title()
        params['sex'] = tfoms_data.get('sex', 0)
        birthDate = datetime.datetime.strptime(tfoms_data.get('birthdate'), '%d.%m.%Y')
        params['birthDate'] = calendar.timegm(birthDate.timetuple()) * 1000
        params['documentSerial'] = tfoms_data.get('doc_series', '')
        params['documentNumber'] = tfoms_data.get('doc_number', '')
        params['documentTypeCode'] = str(tfoms_data.get('doc_code', ''))
        params['policySerial'] = tfoms_data.get('policy_series', '')
        params['policyNumber'] = tfoms_data.get('policy_number', '')
        params['policyTypeCode'] = str(_tfoms_to_core_policy_type[int(tfoms_data.get('policy_doctype'))])
        params['policyInsurerInfisCode'] = tfoms_data.get('insurance_orgcode', '')
        return params

    def __get_patient_by_tfoms_data(self, tfoms_data):
        patient = self.Struct(success=False, patientId=None, message=None)
        if isinstance(tfoms_data, list) and len(tfoms_data) == 1:
            tfoms_data = tfoms_data[0]
        else:
            patient.message = u'''Идентифицировать пациента по имеющимся данным невозможно,
            необходимо обратиться в регистратуру медицинского учреждения для обновления анкетных данных'''
            return patient
        params = self.__prepare_tfoms_data(tfoms_data)
        try:
            patient = self.client.findPatientByPolicyAndDocument(FindPatientByPolicyAndDocumentParameters(**params))
        except NotFoundException, e:
            try:
                patient = self.client.addPatient(AddPatientParameters(**params))
                patient.message = u'''Пациент не был ранее зарегистрирован в выбранном медицинском учреждении,
                перед обращением к врачу требуется обратиться в регистратуру для подтверждения записи
                и получения карточки'''
            except WebFault, e:
                print e
            except Exception, e:
                print e
        except InvalidPersonalInfoException, e:
            patient.message = u'''Идентифицировать пациента по имеющимся данным невозможно,
            необходимо обратиться в регистратуру медицинского учреждения для обновления анкетных данных'''
        except InvalidDocumentException, e:
            patient.message = u'''Идентифицировать пациента по имеющимся данным невозможно,
            необходимо обратиться в регистратуру медицинского учреждения для обновления анкетных данных'''
        except AnotherPolicyException, e:
            patient.patientId = e.patientId
            patient.success = True
            try:
                result = self.__update_policy(patient.patientId, params)
            except PolicyTypeNotFoundException, e:
                print e
                patient.message = u'''Перед посещением врача Вам необходимо обратиться
                                    в регистратуру медицинского учреждения для обновления анкетных данных'''
            except NotFoundException, e:
                print e
                patient.message = u'''Перед посещением врача Вам необходимо обратиться
                                    в регистратуру медицинского учреждения для обновления анкетных данных'''
            else:
                if result is False:
                    patient.message = u'''Перед посещением врача Вам необходимо обратиться
                                        в регистратуру медицинского учреждения для обновления анкетных данных'''
            #patient.message = u'''Введён неактуальный номер полиса. Перед обращением к врачу требуется обратиться
            #в регистратуру медицинского учреждения для обновления анкетных данных'''
        except NotUniqueException, e:
            patient.message = u'''Идентифицировать пациента по имеющимся данным невозможно,
            необходимо обратиться в регистратуру медицинского учреждения для обновления анкетных данных'''
        return patient

    def __get_patient(self, data, tfoms_data=None):
        """Получение ID пациента в БД ЛПУ
        1. Пациент найден в ТФОМС:
            1.1. Если пациент найден в ЛПУ, то возвращается его ID
            1.2. Если пациент найден в ЛПУ, но полис не совпадает, то проверяем его по документам полученным из ТФОМС,
            если найден по документам, то обновляем его полис в БД ЛПУ и возвращаем ID пациента
            (должны уведомить пользователя о несовпадении полиса и необходимости перед обращением к врачу
            обратиться в регистратуру)
            1.3. Если пациент найден в ЛПУ по ФИО, но ни один документ не совпал
            (или найдено несколько пациентов с такими данными), то вернуть ошибку
            "Идентифицировать пациента по имеющимся данным невозможно,
            необходимо обратиться в регистратуру медицинского учреждения для обновления анкетных данных"
            1.4. Если в БД ЛПУ не найден пациент и не найден ни один из документов,
            то создаём нового пациента по данным, полученным из ТФОМС.
            Возвращаем его ID, уведомляем о том, что
            "пациент не был ранее зарегистрирован в выбранном медицинском учреждении
            и требуется обратиться в регистратуру для регистрации перед обращением к врачу"
        2. Если пациент не найден в ТФОМС, тогда работаем с БД ЛПУ по старой схеме.
        Уточнение: если пациент не найден в БД ЛПУ, вернуть сообщение:
        "такого пациента нет ни в базе застрахованных по ОМС лиц,
        ни в базе медицинского учреждения и необходимо сначала получить полис,
        а потом зарегистрироваться в нужном медицинском учреждении в регистратуре"
        3. В ТФОМС найден полис, но не совпали ФИО или Д.Р., то в БД ЛПУ не ищем, возвращаем сообщение:
        "данные в базе застрахованных по ОМС лиц не совпадают с введенными и запись на прием выполнена быть не может,
        проверьте корректность введенных данных или обратитесь в регистратуру выбранного медицинского учреждения"
        4. Если сервис ТФОМС вернул ошибку, то работаем с БД ЛПУ по старой схеме.
        """
        patient = self.Struct(success=False, patientId=None, message=None)
        if tfoms_data is None or tfoms_data['status'].code == AnswerCodes(0).code:
            patient = self.__get_patient_by_lpu(data)
        elif tfoms_data['status'].code == AnswerCodes(1).code:
            patient = self.__get_patient_by_lpu(data)
            #if patient.success is False and patient.message is None:
            if patient.success is False:
                patient.message = u'''Такого пациента нет ни в базе застрахованных по ОМС лиц,
                                  ни в базе медицинского учреждения. Необходимо получить полис,
                                  а затем зарегистрироваться в регистратуре выбранного медицинского учреждения '''
        elif tfoms_data['status'].code == AnswerCodes(2).code and tfoms_data['data']:
            patient = self.__get_patient_by_lpu(data)
            if patient.success is False and patient.patientId is None:
                try:
                    patient = self.__get_patient_by_tfoms_data(tfoms_data['data'])
                except TApplicationException, e:
                    print e
        elif tfoms_data['status'].code == AnswerCodes(3).code:
            patient.message = u'''Введенные данные не совпадают с данными в базе лиц застрахованных по ОМС.
            Запись на прием не может быть выполнена, проверьте корректность введенных данных
            или обратитесь в регистратуру выбранного медицинского учреждения'''
        return patient

    def __enqueue_patient(self, patient_id, data):
        try:
            date_time = data.get('timeslotStart', datetime.datetime.now())
            params = EnqueuePatientParameters(
                patientId=int(patient_id),
                personId=int(data.get('doctorUid')),
                dateTime=int(calendar.timegm(date_time.timetuple()) * 1000),
                note=data.get('E-mail', 'E-mail'),
                hospitalUidFrom=data.get('hospitalUidFrom'),
#               serverId = data.get('serverId'),
            )
        except Exception, e:
            print e
            raise exceptions.ValueError
        else:
            try:
                result = self.client.enqueuePatient(params)
                print result
            except WebFault, e:
                print e
            except Exception, e:
                print e
                return {'result': False,
                        'error_code': e.message,
                        'ticketUid': ''}
            else:
                if result.success:
                    return {'result': True,
                            'error_code': result.message,
                            'message': result.message,
                            'ticketUid': str(result.queueId) + '/' + str(patient_id),
                            'patient_id': patient_id}
                else:
                    return {'result': False,
                            'error_code': result.message,
                            'ticketUid': ''}
        return None

    def __update_policy_type_code(self, data, _type='core'):
        document = data.get('document')
        if document and 'policy_type' in document:
            try:
                data['document']['policy_type'] = str(
                    _policy_types_mapping[int(data['document']['policy_type'])][_type])
            except NameError:
                pass
        return data

    def enqueue(self, **kwargs):
        """Записывает пациента на приём

        Args:
            person: словарь с данными о пациенте (обязательный):
                {'lastName': фамилия
                'firstName': имя
                'patronymic': отчество}
            hospitalUidFrom: id ЛПУ, из которого производится запись (необязательный)

        """
        ################################################################
        # Search in TFOMS
        ################################################################
        tfoms_result = None
        tfoms_params = self.__prepare_tfoms_params(self.__update_policy_type_code(kwargs, 'tfoms'))
        try:
            tfoms_result = self.__check_by_tfoms(tfoms_params)
            logger.debug('QUERY TO TFOMS WAS SENT')
        except Exception, e:
            logger.error(e)
            print e
        ################################################################
        # TODO: избавиться от костыля.
        kwargs = self.__update_policy_type_code(kwargs, 'core')

        patient = self.__get_patient(kwargs, tfoms_result)
        if patient and patient.success and patient.patientId:
            result = self.__enqueue_patient(patient.patientId, kwargs)
            message = getattr(patient, 'message', None)
            if message:
                result['message']=message
            return result
        else:
            return {'result': False,
                    'message': getattr(patient, 'message', ''),
                    'error_code': getattr(patient, 'message', '')}

    def dequeue(self, server_id, patient_id, ticket_id):
        if server_id and patient_id and ticket_id:
            try:
                result = self.client.dequeuePatient(patientId=patient_id, queueId=ticket_id)
            except NotFoundException, e:
                print e.error_msg
                return {'success': False, 'comment': e.error_msg, }
            except TException, e:
                print e
                return {'success': False, 'comment': e.message, }
            else:
                message = getattr(result, 'message', None)
                if not message:
                    message = u'Запись на приём отменена.' if result.success else u'Ошибка отмены записи на приём.'
                return dict(success=result.success, comment=message)
        else:
            raise exceptions.ValueError


class ClientEPGU():
    """Класс клиента для взаимодействия с ЕПГУ"""

    def __init__(self):
        self.url = settings.EPGU_SERVICE_URL
        self.client = None
        self.jinja2env = Environment(loader=PackageLoader('int_service', 'templates'))

    def __check_url(self, url):
        try:
            if urllib2.urlopen(url, timeout=2).getcode() == 200:
                return True
        except urllib2.URLError, e:
            print e
        except socket.timeout, e:
            print e
        return False

    def __init_client(self):
        if not self.client:
            if self.__check_url(self.url):
                if settings.DEBUG:
                    self.client = Client(self.url, cache=None)
                else:
                    self.client = Client(self.url)

    def __send(self, method, message=None):
        self.__init_client()
        params = dict()
        params['messageCode'] = method
        if message:
            params['message'] = base64.b64encode(message.encode('utf-8'))
        if self.client:
            return self.client.service.Send(MessageData={'AppData': params})
        else:
            return None

    def __generate_message(self, params):
        template = self.jinja2env.get_template('epgu_message.tpl')
        if isinstance(params, list):
            result = []
            for value in params:
                result.append(self.__generate_message(value))
            return u''.join(result)
        if isinstance(params, dict):
            for k, v in params.items():
                if isinstance(v, (dict, list)) and k != 'params':
                    params[k] = self.__generate_message(v)
        return self.__strip_message(template.render(params=params))

    def __strip_message(self, message):
        return u''.join([string.strip() for string in message.splitlines()])

    def GetMedicalSpecializations(self, auth_token):
        """Получает список специальностей из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)

        <medical-specialization>
            <id>4f882b982bcfa5145a00036c</id>
            <name>Аллергология и иммунология</name>
            <description/>
        </medical-specialization>
        <medical-specialization>
            <id>4f882b982bcfa5145a00036d</id>
            <name>Анестезиология и реаниматология</name>
            <description/>
        </medical-specialization>
        <medical-specialization>
            <id>4f882b982bcfa5145a00036e</id>
            <name>Гастроэнтерология</name>
            <description/>
        </medical-specialization>

        Тег id – идентификатор специальности в справочнике ЕПГУ
        Тег name – название специальности в справочнике ЕПГУ
        """
        try:
            message = self.__generate_message(dict(params={'auth_token': auth_token}))
            result = self.__send('GetMedicalSpecializations', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            medical_specializations = getattr(result.AppData, 'medical-specializations', None)
            if medical_specializations:
                return medical_specializations
            return getattr(result.AppData, 'errors', None)
        return None

    def GetReservationTypes(self, auth_token):
        """Получает список типов записи из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)

        <reservation-type>
            <id>4f8805b52bcfa52299000011</id>
            <name>Автоматическая запись</name>
            <code>automatic</code>
        </reservation-type>
        <reservation-type>
            <id>4f8805b52bcfa52299000013</id>
            <name>Запись по листу ожидания</name>
            <code>waiting_list</code>
        </reservation-type>
        <reservation-type>
            <id>4f8805b52bcfa52299000012</id>
            <name>Запись с подтверждением</name>
            <code>manual</code>
        </reservation-type>

        Тег id – идентификатор типа записи в справочнике ЕПГУ
        Тег name – название типа записи в справочнике ЕПГУ
        Тег code – код типа записи в справочнике ЕПГУ

        По умолчанию использовать значение automatic.
        """
        try:
            message = self.__generate_message(dict(params={'auth_token': auth_token}))
            result = self.__send('GetReservationTypes', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            reservation_types = getattr(result.AppData, 'reservation-types', None)
            if reservation_types:
                return reservation_types
            return getattr(result.AppData, 'errors', None)
        return None

    def GetPaymentMethods(self, auth_token):
        """Получает список методов оплаты из ЕПГУ

        Args:
            auth_token: указывается token ЛПУ (обязательный)

        <payment-method>
            <id>4f8804ab2bcfa520e6000003</id>
            <name>Бюджетные пациенты</name>
            <default/>
        </payment-method>
        <payment-method>
            <id>4f8804ab2bcfa520e6000002</id>
            <name>Пациенты ДМС</name>
            <default/>
        </payment-method>
        <payment-method>
            <id>4f8804ab2bcfa520e6000001</id>
            <name>Пациенты с полисами ОМС</name>
            <default>true</default>
        </payment-method>


        Тег id – идентификатор метода оплаты в справочнике ЕПГУ
        Тег name – название метода оплаты в справочнике ЕПГУ
        Тег default – используется ли данный метод по умолчанию

        По умолчанию для значения Пациенты с полисами ОМС использовать тег default = true.
        """
        try:
            message = self.__generate_message(dict(params=dict(auth_token=auth_token)))
            result = self.__send('GetPaymentMethods', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            payment_methods = getattr(result.AppData, 'payment-methods', None)
            if payment_methods:
                return payment_methods
            return getattr(result.AppData, 'errors', None)
        return None

    def GetServiceTypes(self, auth_token, ms_id=None):
        """Получает список медицинских услуг из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)
            ms_id: указывается идентификатор медицинской специализации (необязательный)

        <service-type>
            <id>4f993422ef245509c20001d3</id>
            <name>Ангиография артерии верхней конечности прямая</name>
            <recid>828</recid>
            <code>A0612018</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001d4</id>
            <name>Ангиография артерии верхней конечности ретроградная</name>
            <recid>829</recid>
            <code>A0612019</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001c9</id>
            <name>Ангиография артерии щитовидной железы</name>
            <recid>818</recid>
            <code>A0612008</code>
        </service-type>

        Тег id – идентификатор метода оплаты в справочнике ЕПГУ
        Тег name – название метода оплаты в справочнике ЕПГУ

        По умолчанию для значения Пациенты с полисами ОМС использовать тег default = true.
        """
        try:
            params = dict(auth_token=auth_token)
            if ms_id:
                params.update(dict(ms_id=ms_id))
            message = self.__generate_message(dict(params=params))
            result = self.__send('GetServiceTypes', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            service_types = getattr(result.AppData, 'service-types', None)
            if service_types:
                return service_types
            return getattr(result.AppData, 'errors', None)
        return None

    def GetServiceType(self, auth_token, service_type_id):
        """Получает вид услуги по идентификатору из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)
            ms_id: указывается идентификатор медицинской услуги (обязательный)

        <service-type>
            <id>4f993422ef245509c20001d3</id>
            <name>Ангиография артерии верхней конечности прямая</name>
            <recid>828</recid>
            <code>A0612018</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001d4</id>
            <name>Ангиография артерии верхней конечности ретроградная</name>
            <recid>829</recid>
            <code>A0612019</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001c9</id>
            <name>Ангиография артерии щитовидной железы</name>
            <recid>818</recid>
            <code>A0612008</code>
        </service-type>

        Тег id – идентификатор метода оплаты в справочнике ЕПГУ
        Тег name – название метода оплаты в справочнике ЕПГУ

        По умолчанию для значения Пациенты с полисами ОМС использовать тег default = true.
        """
        try:
            message = self.__generate_message(dict(params={'auth_token': auth_token,
                                                           ':service_type_id': service_type_id}))
            result = self.__send('GetServiceType', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            service_type = getattr(result.AppData, 'service-type', None)
            if service_type:
                return service_type
            return getattr(result.AppData, 'errors', None)
        return None

    def GetPlaces(self, **kwargs):
        pass

    def GetPlace(self, auth_token, place_id='current'):
        """Получает код ЛПУ из БД ЕПГУ

        Args:
            auth_token: указывается token ЛПУ (обязательный)
            place_id: всегда указывается current (??) (обязательный)

        Returns:
            Идентификатор ЛПУ. Пример:
            {'id': '4f880ca42bcfa5277202f051',
             'name': u'ГУЗ "ПЕНЗЕНСКАЯ ОБЛАСТНАЯ КЛИНИЧЕСКАЯ БОЛЬНИЦА ИМ.Н.Н.БУРДЕНКО"'
             }

        """
        try:
            message = self.__generate_message(dict(params={':place_id': place_id, 'auth_token': auth_token}))
            result = self.__send('GetPlace', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            if result:
                places = getattr(result.AppData, 'places', None)
                if places:
                    return places
                return getattr(result.AppData, 'errors', None)
        return None

    def GetLocations(self, hospital, service_type_id=None, page=1):
        """Получает список врачей для указанного ЛПУ по указанному типу услуг

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            service_type_id: идентификатор услуги в ЕПГУ, получаемый в GetServiceType (необязательный)
            page: (необязательный) № страницы. По умолчанию 1-я, количество записей на странице - 10 шт

        Returns:
            массив ФИО врачей:
            [{'prefix': u'Ененко У.С. - хирург', }]

        """
        try:
            params = {':place_id': hospital['place_id'],
                      'auth_token': hospital['auth_token'],
                      'page': page}
            if service_type_id:
                params['service_type_id'] = service_type_id,
            message = self.__generate_message(dict(params=params))
            result = self.__send('GetLocations', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            place_locations_data = getattr(result.AppData, 'place-locations-data', None)
            if place_locations_data:
                return place_locations_data
            return getattr(result.AppData, 'errors', None)
        return None

    def GetLocation(self):
        pass

    def DeleteEditLocation(self, hospital, location_id):
        """Помечает врача как удаленного на ЕПГУ

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            location_id: (обязательный) идентификатор редактируемой очереди

        """
        try:
            params = dict()
            params['params'] = {'auth_token': hospital['auth_token'],
                                ':place_id': hospital['place_id'],
                                ':location_id': location_id,
                                }
            message = self.__generate_message(params)
            result = self.__send('DeleteEditLocation', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def PostLocations(self, hospital, doctor, service_types, can_write=None):
        """Используется для создания очереди в федеральной регистратуре (на ЕПГУ)

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            doctor: (обязательный) словарь с информацией о враче, вида:
                {'prefix': название очереди (ФИО?),
                 'medical_specialization_id': код специальности (Speciality.nameEPGU),
                 'cabinet_number': ?? номер кабинета (#TODO: дописать ИС для получение кабинета),
                 'time_table_period': количество дней на которое будет доступно расписание
                    (Определяется максимальной датой, на которую доступно расписание для данного врача.
                    Данный параметр можно вынести в файл настроек. По умолчанию значение 90)
                 'reservation_time': время (в минутах) приема врача
                    (необходимо высчитывать время приема для каждого врача индивидуально как разницу между началом и
                    окончанием приема одного пациента на первый день получаемого расписания),
                 'reserved_time_for_slot': время между талонами на прием (?равно времени указанном в reservation_time),
                 'reservation_type_id': идентификатор типа записи, полученный в GetServiceType,
                 'payment_method_id': идентификатор вида оплаты, полученный в GetPaymentMethods,
                }
            service_types: (обязательный) список кодов мед. услуг из GetServiceType, вида:
                ['4f882b9c2bcfa5145a0006e8', ]
            can_write: (необязательный) строка через запятую без пробелов из тех,
                кто имеет доступ к записи в данную очередь. если массив пустой, то записаться никто не сможет.
                если параметр не присылать, то по умолчанию доступ к записи имеют все
                (возможные значения: registry, epgu, call_center, terminal, mis);

        Returns:
            Словарь с информацией о созданной записи, вида:
            {'created-at': '2012-09-12T14:59:04+04:00',
             'id': '50506af8bb4d3371b8028ea3',
             'medical-specialization-id': '4f882b982bcfa5145a000383'
            }

        """
        try:
            params = dict()
            try:
                params['prefix'] = doctor['prefix']
                params['medical_specialization_id'] = doctor['medical_specialization_id']
                params['cabinet_number'] = doctor['cabinet_number']
                params['time_table_period'] = doctor['time_table_period']
                params['reservation_time'] = doctor['reservation_time']
                params['reserved_time_for_slot'] = doctor['reserved_time_for_slot']
                params['reservation_type_id'] = doctor['reservation_type_id']
                params['payment_method_id'] = doctor['payment_method_id']

                if can_write:
                    params['can_write'] = can_write

                service_type_ids = dict()
                for k, service_type in enumerate(service_types):
                    service_type_ids['st%d' % k] = service_type
                params['service_types_ids'] = service_type_ids

                params['params'] = {':place_id': hospital['place_id'], 'auth_token': hospital['auth_token']}
            except AttributeError, e:
                print e
                return None
            else:
                message = self.__generate_message(dict(location=params))
                result = self.__send('PostLocations', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            location = getattr(result.AppData, 'location', None)
            if location:
                return location
            return getattr(result.AppData, 'errors', None)
        return None

    def PutEditLocation(self, hospital, doctor, service_types, can_write=None):
        """Используется для редактировани очереди в федеральной регистратуре (на ЕПГУ)

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            doctor: (обязательный) словарь с информацией о враче, вида:
                {'prefix': название очереди (ФИО?),
                 'location_id': идентификатор врача (очереди),
                 'medical_specialization_id': код специальности (Speciality.nameEPGU),
                 'cabinet_number': номер кабинета ,
                 'time_table_period': количество дней на которое будет доступно расписание
                    (Определяется максимальной датой, на которую доступно расписание для данного врача.
                    Данный параметр можно вынести в файл настроек. По умолчанию значение 90)
                 'reservation_time': время (в минутах) приема врача
                    (необходимо высчитывать время приема для каждого врача индивидуально как разницу между началом и
                    окончанием приема одного пациента на первый день получаемого расписания),
                 'reserved_time_for_slot': время между талонами на прием (?равно времени указанном в reservation_time),
                 'reservation_type_id': идентификатор типа записи, полученный в GetServiceType,
                 'payment_method_id': идентификатор вида оплаты, полученный в GetPaymentMethods,
                }
            service_types: (обязательный) список кодов мед. услуг из GetServiceType, вида:
                ['4f882b9c2bcfa5145a0006e8', ]
            can_write: (необязательный) строка через запятую без пробелов из тех,
                кто имеет доступ к записи в данную очередь. если массив пустой, то записаться никто не сможет.
                если параметр не присылать, то по умолчанию доступ к записи имеют все
                (возможные значения: registry, epgu, call_center, terminal, mis);

        Returns:
            Словарь с информацией о созданной записи, вида:
            {'created-at': '2012-09-12T14:59:04+04:00',
             'id': '50506af8bb4d3371b8028ea3',
             'medical-specialization-id': '4f882b982bcfa5145a000383'
            }

        """
        try:
            params = dict()
            try:
                params['prefix'] = doctor['prefix']
                params['medical_specialization_id'] = doctor['medical_specialization_id']
                params['cabinet_number'] = doctor['cabinet_number']
                params['time_table_period'] = doctor['time_table_period']
                params['reservation_time'] = doctor['reservation_time']
                params['reserved_time_for_slot'] = doctor['reserved_time_for_slot']
                params['reservation_type_id'] = doctor['reservation_type_id']
                params['payment_method_id'] = doctor['payment_method_id']

                service_type_ids = dict()
                for k, service_type in enumerate(service_types):
                    service_type_ids['st%d' % k] = service_type
                params['service_types_ids'] = service_type_ids

                params['params'] = {':place_id': hospital['place_id'],
                                    'auth_token': hospital['auth_token'],
                                    ':location_id': doctor['location_id']}
            except AttributeError, e:
                print e
                return None
            else:
                message = self.__generate_message(dict(location=params))
                result = self.__send('PutEditLocation', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            location = getattr(result.AppData, 'location', None)
            if location:
                return location
            return getattr(result.AppData, 'errors', None)
        return None

    def PostRules(self, hospital, doctor, period, days, can_write=None):
        """Добавляет расписание на ЕПГУ

        Args:
            doctor: (обязательный) строка, ФИО врача,
            period: (обязательный) строка, период, на которые передаётся расписание,
            days: (обязательный) массив, содержащий расписание по датам, вида:
                [{'date': дата,
                  'interval': - массив интервалов, вида:
                      [{'start': время начала приёма,
                      'end': время окончания приёма,},
                      {'start': время начала приёма,
                      'end': время окончания приёма,},
                      ]
                }],
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            can_write: (необязательный) строка через запятую без пробелов из тех,
                кто имеет доступ к записи в данную очередь. если массив пустой, то записаться никто не сможет.
                если параметр не присылать, то по умолчанию доступ к записи имеют все
                (возможные значения: registry, epgu, call_center, terminal, mis);

        Returns:
            Словарь с информацией о созданном расписании, вида:
            {'id': '50507480ef2455c01202a0ca', # идентификатор расписания
             'name': u'Новое расписание', # наименование расписания
            }

        """
        try:
            params = dict()
            try:
                params['schedules_rule'] = dict(name=u'%s (%s)' % (doctor, unicode(period)))

                day_rule = dict()
                for day in days:
                    key = 'day%d' % (day['date'].isoweekday() % 7)
                    day_rule[key] = []
                    for k, interval in enumerate(day['interval']):
                        day_rule[key].append({'int%s' % k: dict(time0=interval['start'], time1=interval['end'])})
                params['day_rule'] = day_rule
                
                if can_write:
                    params['can_write'] = can_write

                params['params'] = {':place_id': hospital['place_id'], 'auth_token': hospital['auth_token']}
            except AttributeError, e:
                print e
                return None
            else:
                message = self.__generate_message(dict(rule_data=params))
                result = self.__send('PostRules', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def PutLocationSchedule(self, hospital, location_id, rules):
        """Связывает сотрудников и расписание

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            location_id: (обязательный) строка, id очереди из PostLocations,
            rules: (обязательный) массив словарей с информацией о расписании, вида:
                [{'id': '50507480ef2455c01202a0ca', # идентификатор расписания из PostRules
                 'start': дата начала действия расписания,
                 'end': дата окончания действия расписания
                },]

        Returns:
            Сообщение об ошибке, либо сообщение об успешной записи


        """
        try:
            params = dict()
            try:
                params['applied_short_day'] = None
                params['applied_nonworking_day'] = None
                params['applied_exception'] = None

                applied_rule = dict()
                for k, v in enumerate(rules):
                    applied_rule['rule%d' % (k + 1)] = dict(rule_id=v['id'],
                                                            start_date=v['start'].strftime('%d.%m.%Y'),
                                                            end_date=v['end'].strftime('%d.%m.%Y'),
                                                            type='all')
                params['applied_rule'] = applied_rule

                params['params'] = {':location_id': location_id, 'auth_token': hospital['auth_token']}
            except AttributeError, e:
                print e
                return None
            else:
                message = self.__generate_message(dict(applied_schedule=params))
                result = self.__send('PutLocationSchedule', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            if result is not None:
                errors = getattr(result.AppData, 'errors', None)
                if errors:
                    return errors
                return result.AppData
        return None

    def PutActivateLocation(self, hospital, location_id):
        """Активирует расписание

        Args:
            location_id: (обязательный) строка, id врача из PostLocations,
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }

        Returns:
            Сообщение об ошибке, либо сообщение об успешной записи

        """
        try:
            message = self.__generate_message(dict(params={':location_id': location_id,
                                                           'auth_token': hospital['auth_token']}))
            result = self.__send('PutActivateLocation', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def PostReserve(self, hospital, doctor_id, service_type_id, date, cito=0):
        """Резервирует время на запись

        Args:
            doctor_id: (обязательный) строка, id врача из PostLocations,
            service_type_id: (обязательный) строка, id типа услуги из GetServiceType,
            date: (обязательный) словарь с информацией о расписании, вида:
                {'date': дата приёма,
                 'start_time': время приёма
                }
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            cito: (необязательный) обозначает, что пациент экстренный и может записаться в любое время.
                Список возможных значений: 0 - не экстренный; 1 - экстренный.  Значение поумолчанию - 0

        Возвращает идентификатор зарезервированного слота

        """
        try:
            params = dict()
            try:
                params['location_id'] = doctor_id
                params['service_type_id'] = service_type_id
                params['date'] = date['date']
                params['start_time'] = date['start_time']

                params['params'] = {'auth_token': hospital['auth_token'], ':cito': cito}
            except AttributeError, e:
                print e
                return None
            else:
                message = self.__generate_message(dict(client_info=params))
                result = self.__send('PostReserve', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            if hasattr(result, 'AppData'):
                errors = getattr(result.AppData, 'errors', None)
                if errors:
                    return errors
                return result.AppData
        return None

    def PutSlot(self, hospital, patient, slot_id):
        """Запрос на получение из федеральной регистратуры факта записи  на оказание услуги

        Args:
            patient: (обязательный) словарь с информацией о пациенте, вида:
                {'name': (обязательный) имя пациента,
                 'surname': (обязательный) фамилия пациента,
                 'patronymic': (необязательный) отчество пациента,
                 'phone': (обязательный) номер телефона в формате +7(код)номер,
                 'id': (обязательный) уникальный идентификатор пациента,
                },
            slot_id: (обязательный) идентификатор зарезервированного слота, в который производится запись,
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }

        """
        try:
            params = dict()
            try:
                params['name'] = base64.b64encode(patient['name'].encode('utf-8'))
                params['surname'] = base64.b64encode(patient['surname'].encode('utf-8'))
                params['patronymic'] = base64.b64encode(patient['patronymic'].encode('utf-8'))
                params['phone'] = patient['phone']
                params['client_id'] = patient['id']

                params['params'] = {'auth_token': hospital['auth_token'], ':slot_id': slot_id}
            except AttributeError, e:
                print e
                return None
            else:
                message = self.__generate_message(dict(client_info=params))
                result = self.__send('PutSlot', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def DeleteSlot(self, hospital, slot_id, comment=None):
        """Отмена записи на прием к врачу из ЛПУ на ЕПГУ

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            slot_id: (обязательный) идентификатор зарезервированного слота, в который производится запись,
            comment: (необязательный) комментарий удаления слота

        """
        try:
            try:
                params = {'auth_token': hospital['auth_token'], ':slot_id': slot_id}
                if comment:
                    params.update(dict(comment=comment))
            except AttributeError, e:
                print e
                return None
            else:
                message = self.__generate_message(dict(params=params))
                result = self.__send('DeleteSlot', message)
        except WebFault, e:
            print e
        except Exception, e:
            print e
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None
