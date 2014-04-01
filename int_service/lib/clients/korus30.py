# -*- coding: utf-8 -*-

import exceptions
import datetime
import calendar
from urlparse import urlparse
from suds import WebFault
from ...lib import is_exceptions
import settings
from copy import deepcopy

from thrift.transport import TTransport, TSocket, THttpClient
from thrift.protocol import TBinaryProtocol, TProtocol
from ..core_services.Communications import Client as Thrift_Client, TApplicationException
from ..core_services.ttypes import GetTimeWorkAndStatusParameters, EnqueuePatientParameters
from ..core_services.ttypes import AddPatientParameters, FindOrgStructureByAddressParameters
from ..core_services.ttypes import FindPatientParameters, FindMultiplePatientsParameters
from ..core_services.ttypes import SQLException, NotFoundException, TException
from ..core_services.ttypes import AnotherPolicyException, InvalidDocumentException, InvalidPersonalInfoException
from ..core_services.ttypes import FindPatientByPolicyAndDocumentParameters, NotUniqueException
from ..core_services.ttypes import ChangePolicyParameters, Policy, PolicyTypeNotFoundException
from ..core_services.ttypes import ScheduleParameters, QuotingType, CouponStatus, ReasonOfAbsenceException

from ..tfoms_service import TFOMSClient, AnswerCodes
from ..utils import logger
from abstract import AbstractClient

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

logger_tags = dict(tags=['korus30', 'IS'])


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
            logger.error(e, extra=logger_tags)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
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
            logger.error(e, extra=logger_tags)
        except NotFoundException, e:
            print e.error_msg
            logger.error(e, extra=logger_tags)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            #return self.__unicode_result(result)
            return result
        return None

    def getSpecialities(self, hospital_uid_from):
        try:
            result = self.client.getSpecialities(hospital_uid_from)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except NotFoundException, e:
            print e.error_msg.encode('utf-8')
            logger.error(e, extra=logger_tags)
        except SQLException, e:
            print e.error_msg
            logger.error(e, extra=logger_tags)
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
                logger.error(e, extra=logger_tags)
            except NotFoundException, e:
                logger.error(e, extra=logger_tags)
                return []
            else:
                #return self.__unicode_result(result)
                return result
        else:
            logger.error(exceptions.AttributeError(), extra=logger_tags)
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
        absences = []
        start = kwargs.get('start')
        end = kwargs.get('end')
        doctor_uid = kwargs.get('doctor_uid')
        if start and end and doctor_uid:
            hospital_uid_from = kwargs.get('hospital_uid_from')
            if not hospital_uid_from:
                hospital_uid_from = ''
                quotingType = QuotingType.FROM_PORTAL
            else:
                quotingType = QuotingType.FROM_OTHER_LPU

            parameters = ScheduleParameters(personId=doctor_uid,
                                            beginDateTime=int(calendar.timegm(start.timetuple()) * 1000),
                                            endDateTime=int(calendar.timegm(end.timetuple()) * 1000),
                                            hospitalUidFrom=hospital_uid_from,
                                            quotingType=quotingType)

            try:
                data = self.client.getPersonSchedule(parameters)
            except NotFoundException, e:
                print e.error_msg
                logger.error(u'{0}{1}'.format(e, kwargs), extra=logger_tags)
            else:
                schedules = getattr(data, 'schedules', dict())
                person_absences = getattr(data, 'personAbsences', dict())
                if schedules:
                    for date_timestamp, schedule in sorted(schedules.items()):
                        if schedule and hasattr(schedule, 'tickets') and schedule.tickets:
                            date = schedule.date
                            for key, timeslot in enumerate(schedule.tickets):
                                start = datetime.datetime.utcfromtimestamp((date + timeslot.begTime) / 1000)
                                finish = datetime.datetime.utcfromtimestamp((date + timeslot.endTime) / 1000)

                                if timeslot.free and timeslot.available:
                                    status = 'free'
                                elif timeslot.free:
                                    status = 'disabled'
                                else:
                                    status = 'locked'

                                result.append({
                                    'start': start,
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

                if person_absences:
                    for date_timestamp, absence in person_absences.items():
                        date = datetime.datetime.utcfromtimestamp(date_timestamp / 1000).date()
                        absences.append(dict(date=date, code=absence.code, name=absence.name))
        else:
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError
        return {'timeslots': result, 'absences': absences}

    def getScheduleInfo_old(self, **kwargs):
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
                    logger.error(e, extra=logger_tags)
                    continue
                else:
                    if timeslot:
                        result.extend(timeslot)
        else:
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError
        return {'timeslots': result}

    def getPatientQueue(self, **kwargs):
        """Возвращает информацию о записях пациента

        Args:
            patientId: id пациента (обязательный)

        """
        patient_id = kwargs.get('patientId')
        if patient_id:
            try:
                result = self.client.getPatientQueue(patient_id)
            except SQLException, e:
                print e.error_msg
                logger.error(e, extra=logger_tags)
            except WebFault, e:
                print e
                logger.error(e, extra=logger_tags)
            else:
                for ticket in result:
                    ticket.dateTime = datetime.datetime.utcfromtimestamp(ticket.dateTime / 1000)
                return result
        else:
            logger.error(exceptions.AttributeError(), extra=logger_tags)
            raise exceptions.AttributeError
        return None

    def getPatientInfo(self, **kwargs):
        """Возвращает информацию о пациенте

        Args:
             patientId: id пациента (обязательный)

        """
        patient_id = kwargs.get('patientId')
        if patient_id:
            if not isinstance(patient_id, list):
                patient_id = [patient_id]
            try:
                result = self.client.getPatientInfo(patient_id)
            except WebFault, e:
                print e
                logger.error(e, extra=logger_tags)
            else:
                return result
        else:
            logger.error(exceptions.AttributeError(), extra=logger_tags)
            raise exceptions.AttributeError
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
        birth_date = kwargs.get('birthDate')
        if isinstance(birth_date, datetime.date):
            birth_date = calendar.timegm(birth_date.timetuple()) * 1000
        if not document:
            document = dict()
        params = {
            'lastName': kwargs.get('lastName'),
            'firstName': kwargs.get('firstName'),
            'patrName': kwargs.get('patrName'),
            'birthDate': birth_date,
            'document': document,
            'sex': kwargs.get('sex'),
        }

        try:
            result = self.client.findPatient(FindPatientParameters(**params))
        except NotFoundException, e:
            logger.error(e, extra=logger_tags)
            raise e
        except TException, e:
            logger.error(e, extra=logger_tags)
            raise e
        except WebFault, e:
            logger.error(e, extra=logger_tags)
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
            logger.error(e, extra=logger_tags)
            raise e
        except TException, e:
            logger.error(e, extra=logger_tags)
            raise e
        except WebFault, e:
            logger.error(e, extra=logger_tags)
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
            logger.error(e, extra=logger_tags)
            print e
        except Exception, e:
            logger.error(e, extra=logger_tags)
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
            logger.error(e, extra=logger_tags)
            print e
        except NotFoundException, e:
            logger.error(e, extra=logger_tags)
            print e.error_msg
        except TApplicationException, e:
            logger.error(e, extra=logger_tags)
            print e
        except ReasonOfAbsenceException, e:
            logger.error(e, extra=logger_tags)
            print e
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
        params = dict()
        #person = data.get('person')
        #params = {'lastName': person.get('lastName'),
        #          'firstName': person.get('firstName'),
        #          'patrName': person.get('patronymic')}

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

    def get_patient(self, patient_params, data):
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
                elif len(patients) == 0:
                    if hospital_uid_from == '0':
                        patient.message = int(is_exceptions.IS_PatientNotRegistered())
                        #return {'result': False, 'error_code': int(is_exceptions.IS_PatientNotRegistered()), }
                else:
                    patient = self.Struct(success=True, patientId=patients[0].id)
        except NotFoundException, e:
            print e
            logger.error(e, extra=logger_tags)
            if hospital_uid_from == '0':
                patient.message = e.error_msg
                #return {'result': False, 'error_code': e.error_msg.decode('utf-8')}
        except TException, e:
            print e
            logger.error(e, extra=logger_tags)
            patient.message = e.message
            #return {'result': False, 'error_code': e.message}
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
            patient.message = e
            #return {'result': False, 'error_code': e}
        return patient

    def __get_patient_by_lpu(self, data):
        """Поиск пациента в БД ЛПУ. Добавление его при записи между ЛПУ"""

        patient_params = self.__prepare_patient_params(data)
        patient = self.get_patient(patient_params, data)
        hospital_uid_from = data.get('hospitalUidFrom')

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
        params['lastName'] = tfoms_data.get('lastName', tfoms_data.get('lastname', '')).title()
        params['firstName'] = tfoms_data.get('firstName', '').title()
        params['patrName'] = tfoms_data.get('patrName', tfoms_data.get('midname', '')).title()
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
            logger.error(e, extra=logger_tags)
            try:
                patient = self.client.addPatient(AddPatientParameters(**params))
                patient.message = u'''Пациент не был ранее зарегистрирован в выбранном медицинском учреждении,
                перед обращением к врачу требуется обратиться в регистратуру для подтверждения записи
                и получения карточки'''
            except WebFault, e:
                logger.error(e, extra=logger_tags)
                print e
            except Exception, e:
                logger.error(e, extra=logger_tags)
                print e
        except InvalidPersonalInfoException, e:
            patient.message = u'''Идентифицировать пациента по имеющимся данным невозможно,
            необходимо обратиться в регистратуру медицинского учреждения для обновления анкетных данных'''
        except InvalidDocumentException, e:
            logger.error(e, extra=logger_tags)
            patient.message = u'''Идентифицировать пациента по имеющимся данным невозможно,
            необходимо обратиться в регистратуру медицинского учреждения для обновления анкетных данных'''
        except AnotherPolicyException, e:
            logger.error(e, extra=logger_tags)
            patient.patientId = e.patientId
            patient.success = True
            try:
                result = self.__update_policy(patient.patientId, params)
            except PolicyTypeNotFoundException, e:
                logger.error(e, extra=logger_tags)
                print e
                patient.message = u'''Перед посещением врача Вам необходимо обратиться
                                    в регистратуру медицинского учреждения для обновления анкетных данных'''
            except NotFoundException, e:
                print e
                logger.error(e, extra=logger_tags)
                patient.message = u'''Перед посещением врача Вам необходимо обратиться
                                    в регистратуру медицинского учреждения для обновления анкетных данных'''
            else:
                if result is False:
                    patient.message = u'''Перед посещением врача Вам необходимо обратиться
                                        в регистратуру медицинского учреждения для обновления анкетных данных'''
            #patient.message = u'''Введён неактуальный номер полиса. Перед обращением к врачу требуется обратиться
            #в регистратуру медицинского учреждения для обновления анкетных данных'''
        except NotUniqueException, e:
            logger.error(e, extra=logger_tags)
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
        3. В ТФОМС найден полис, но не совпал Д.Р., то в БД ЛПУ не ищем, возвращаем сообщение:
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
                    # ELREG-158: Из БД ТФОМС приходят пустые ФИО, поэтому подставляем введённые пользователем
                    patient_params = self.__prepare_patient_params(data)
                    if isinstance(tfoms_data['data'], list) and len(tfoms_data['data']) == 1:
                        tfoms_data['data'][0].update(dict(lastName=patient_params.get('lastName', ''),
                                                          firstName=patient_params.get('firstName', ''),
                                                          patrName=patient_params.get('patrName', '')))
                    patient = self.__get_patient_by_tfoms_data(tfoms_data['data'])
                except TApplicationException, e:
                    logger.error(e, extra=logger_tags)
                    print e
        elif tfoms_data['status'].code == AnswerCodes(3).code:
            patient.message = u'''Введенные данные не совпадают с данными в базе лиц застрахованных по ОМС.
            Запись на прием не может быть выполнена, проверьте корректность введенных данных
            или обратитесь в регистратуру выбранного медицинского учреждения'''

        #Костыль.. убираем сообщение 'ok.' из вывода в результатах записи
        message = getattr(patient, 'message', None)
        if message and message == 'ok.':
            setattr(patient, 'message', '')
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
            logger.error(e, extra=logger_tags)
            print e
            raise exceptions.ValueError
        else:
            try:
                result = self.client.enqueuePatient(params)
                print result
            except WebFault, e:
                logger.error(e, extra=logger_tags)
                print e
            except Exception, e:
                logger.error(e, extra=logger_tags)
                print e
                return {'result': False,
                        'error_code': e.message,
                        'ticketUid': ''}
            else:
                if result.success:
                    return {'result': True,
                            'error_code': result.message,
                            'message': result.message if result.message != 'ok.' else '',
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
            except NameError, e:
                logger.error(e, extra=logger_tags)
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
        tfoms_params = self.__prepare_tfoms_params(self.__update_policy_type_code(deepcopy(kwargs), 'tfoms'))
        try:
            tfoms_result = self.__check_by_tfoms(tfoms_params)
            logger.debug('QUERY TO TFOMS WAS SENT', extra=logger_tags)
        except Exception, e:
            logger.error(e, extra=logger_tags)
            print e
        ################################################################
        # TODO: избавиться от костыля.
        kwargs = self.__update_policy_type_code(deepcopy(kwargs), 'core')

        patient = self.__get_patient(kwargs, tfoms_result)
        if patient and patient.success and patient.patientId:
            result = self.__enqueue_patient(patient.patientId, kwargs)
            message = getattr(patient, 'message', None)
            if message:
                result['message'] = message
            return result
        else:
            return {'result': False,
                    'message': getattr(patient, 'message', ''),
                    'error_code': getattr(patient, 'message', '')}

    def dequeue(self, server_id, patient_id, ticket_id):
        if server_id and patient_id and ticket_id:
            try:
                result = self.client.dequeuePatient(patientId=int(patient_id), queueId=int(ticket_id))
            except NotFoundException, e:
                print e.error_msg
                logger.error(e, extra=logger_tags)
                return {'success': False, 'comment': e.error_msg, }
            except TException, e:
                print e
                logger.error(e, extra=logger_tags)
                return {'success': False, 'comment': e.message, }
            else:
                message = getattr(result, 'message', None)
                if not message:
                    message = u'Запись на приём отменена.' if result.success else u'Ошибка отмены записи на приём.'
                return dict(success=result.success, comment=message)
        else:
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError

    def get_closest_free_ticket(self, doctor_id, start=None):
        """Получение ближайшего свободного талончика

        Args:
            doctor_id: идентификатор врача в БД ЛПУ, для которого получаем талончик
            start: дата и время, начиная с которого осуществляется поиск талончика

        """
        if doctor_id:
            if start is None:
                start = datetime.datetime.now()
            try:
                # CORE v2.5.2
        # quotingType=QuotingType.FROM_PORTAL - т.к. этот метод никто, кроме портала не использует, то можно передавать
                parameters = ScheduleParameters(personId=doctor_id,
                                                beginDateTime=int(calendar.timegm(start.timetuple()) * 1000),
                                                hospitalUidFrom='',
                                                quotingType=QuotingType.FROM_PORTAL)

                ticket = self.client.getFirstFreeTicket(parameters)
            except NotFoundException, e:
                print e.error_msg
                logger.error(e, extra=logger_tags)
                return None
            except TApplicationException, e:
                print e
                logger.error(e, extra=logger_tags)
                # CORE v2.4.7
                # TODO: remove lagacy
                try:
                    ticket = self.client.getFirstFreeTicket(
                        personId=doctor_id,
                        dateTime=int(calendar.timegm(start.timetuple()) * 1000),
                        hospitalUidFrom='')
                except NotFoundException, e:
                    logger.error(e, extra=logger_tags)
                    print e.error_msg
                    return None
                else:
                    result = dict(timeslotStart=datetime.datetime.utcfromtimestamp(ticket.begDateTime / 1000),
                                  timeslotEnd=datetime.datetime.utcfromtimestamp(ticket.endDateTime / 1000),
                                  office=ticket.office,
                                  doctor_id=ticket.personId)
                    return result
            except TypeError, e:
                print e
                logger.error(e, extra=logger_tags)
                # CORE v2.4.7
                # TODO: remove lagacy
                try:
                    ticket = self.client.getFirstFreeTicket(
                        personId=doctor_id,
                        dateTime=int(calendar.timegm(start.timetuple()) * 1000),
                        hospitalUidFrom='')
                except NotFoundException, e:
                    print e.error_msg
                    logger.error(e, extra=logger_tags)
                    return None
                else:
                    result = dict(timeslotStart=datetime.datetime.utcfromtimestamp(ticket.begDateTime / 1000),
                                  timeslotEnd=datetime.datetime.utcfromtimestamp(ticket.endDateTime / 1000),
                                  office=ticket.office,
                                  doctor_id=ticket.personId)
                    return result
            except Exception, e:
                print e
                logger.error(e, extra=logger_tags)
                # CORE v2.4.7
                # TODO: remove lagacy
                try:
                    ticket = self.client.getFirstFreeTicket(
                        personId=doctor_id,
                        dateTime=int(calendar.timegm(start.timetuple()) * 1000),
                        hospitalUidFrom='')
                except NotFoundException, e:
                    print e.error_msg
                    logger.error(e, extra=logger_tags)
                    return None
                else:
                    result = dict(timeslotStart=datetime.datetime.utcfromtimestamp(ticket.begDateTime / 1000),
                                  timeslotEnd=datetime.datetime.utcfromtimestamp(ticket.endDateTime / 1000),
                                  office=ticket.office,
                                  doctor_id=ticket.personId)
                    return result
            else:
                beg_date_time = ticket.date + ticket.begTime
                end_date_time = ticket.date + ticket.endTime
                result = dict(timeslotStart=datetime.datetime.utcfromtimestamp(beg_date_time / 1000),
                              timeslotEnd=datetime.datetime.utcfromtimestamp(end_date_time / 1000),
                              office=ticket.office,
                              doctor_id=doctor_id)
                return result
        return None

    def get_new_tickets(self):
        """Получает новые талончики, которые были созданы внутри ЛПУ.
        Будут использованы для отправки на ЕПГУ
        """
        try:
            result = self.client.checkForNewQueueCoupons()
        except TException, e:
            logger.error(e, extra=logger_tags)
            raise e
        except WebFault, e:
            logger.error(e, extra=logger_tags)
            print e
        else:
            return result
        return None

    def get_patient_tickets(self, data):
        try:
            data['person'] = dict(firstName=data['firstName'],
                                  lastName=data['lastName'],
                                  patronymic=data['patronymic'])
            data = self.__update_policy_type_code(deepcopy(data), 'core')
            patient_params = self.__prepare_patient_params(data)
            patient = self.get_patient(patient_params, data)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
            return dict(status=False, message=u'Пациент не найден')
        else:
            if patient and patient.success and patient.patientId:
                tickets = self.getPatientQueue(patientId=patient.patientId)
                if not tickets:
                    return dict(status=False, message=u'Талончики не найдены')
                else:
                    return dict(status=True, message=u'Талончики найдены', tickets=tickets, patient=patient)
            elif hasattr(patient, 'message'):
                return dict(status=False, message=patient.message)
        return dict(status=False, message=u'Пациент не найден')