# -*- coding: utf-8 -*-
import exceptions
import datetime
from suds import WebFault
from ...lib import is_exceptions
import settings
from ..tfoms_service import TFOMSClient, AnswerCodes
from suds.client import Client
from abstract import AbstractClient

from ..utils import logger

logger_tags = dict(tags=['korus20', 'IS'])


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
            logger.error(e, extra=logger_tags)
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
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            return result
        return None

    def getSpecialities(self, hospital_uid_from):
        try:
            result = self.client.service.getSpecialities(hospitalUidFrom=hospital_uid_from)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
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
                logger.error(e, extra=logger_tags)
            else:
                return result['list']
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
            logger.error(exceptions.AttributeError(), extra=logger_tags)
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
            logger.error(e, extra=logger_tags)
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
                logger.error(e, extra=logger_tags)
            else:
                return result['list']
        else:
            logger.error(exceptions.ValueError(), extra=logger_tags)
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
                logger.error(e, extra=logger_tags)
            else:
                return result['patientInfo']
        else:
            logger.error(exceptions.ValueError(), extra=logger_tags)
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
        except exceptions.KeyError, e:
            logger.error(e, extra=logger_tags)
            pass
        else:
            try:
                result = self.client.service.findPatients(**params)
            except WebFault, e:
                print e
                logger.error(e, extra=logger_tags)
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
        except exceptions.KeyError, e:
            logger.error(e, extra=logger_tags)
            pass
        else:
            try:
                result = self.client.service.findPatient(**params)
            except WebFault, e:
                print e
                logger.error(e, extra=logger_tags)
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
                logger.error(e, extra=logger_tags)
            else:
                return result
        else:
            logger.error(exceptions.AttributeError(), extra=logger_tags)
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
            logger.error(exceptions.AttributeError(), extra=logger_tags)
            raise exceptions.AttributeError

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
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError
        else:
            try:
                result = self.client.service.enqueuePatient(**params)
            except WebFault, e:
                print e
                logger.error(e, extra=logger_tags)
            else:
                if result.success:
                    return {
                        'result': True,
                        'message': result.message if result.message != '100 ok' else '',
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
                logger.error(e, extra=logger_tags)
            else:
                return dict(
                    success=result.success,
                    comment=u'Запись на приём отменена.' if result.success else u'Ошибка отмены записи на приём.')
        else:
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError
        return None

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
                ticket = self.client.service.getFirstFreeTicket(
                    personId=doctor_id,
                    start=start,
                    hospitalUidFrom='')
            except WebFault, e:
                print e
                logger.error(e, extra=logger_tags)
            else:
                result = dict(timeslotStart=ticket.begDateTime,
                              timeslotEnd=ticket.endDateTime,
                              office=ticket.office,
                              doctor_id=ticket.personId)
                return result
        return None

    def __prepare_tickets_info(self, tickets):
        for ticket in tickets:
            setattr(ticket, 'dateTime', datetime.datetime.combine(ticket.date, ticket.time))
            del ticket.date
            del ticket.time
        return tickets

    def get_patient_tickets(self, params):
        try:
            patient = self.findPatient(**params)
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
                    return dict(status=True,
                                message=u'Талончики найдены',
                                tickets=self.__prepare_tickets_info(tickets),
                                patient=patient)
        return dict(status=False, message=u'Пациент не найден')