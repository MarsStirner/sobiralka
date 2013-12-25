# -*- coding: utf-8 -*-
import exceptions
from suds.client import Client
from suds import WebFault
from abstract import AbstractClient


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

