# -*- coding: utf-8 -*-

import exceptions
import datetime
from abc import ABCMeta, abstractmethod, abstractproperty
from suds.client import Client
from suds import WebFault
import is_exceptions

class Clients(object):
    '''
    Class provider for current Clients
    '''
    @classmethod
    def provider(cls, type, proxy_url):
        type = type.lower()

        if type == 'samson':
            obj = ClientSamson(proxy_url)
        elif type == 'intramed':
            obj = ClientIntramed(proxy_url)
        elif type == 'core':
            obj = ClientCore(proxy_url)
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

class ClientSamson(AbstractClient):
    def __init__(self, url):
        self.client = Client(url, cache=None)

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
                      'corpus': kwargs['corpus'],
                      'pointKLADR': kwargs['pointKLADR'],
                      'streetKLADR': kwargs['streetKLADR'],
                      'flat': kwargs['flat'],
                      }
            try:
                result = self.client.service.findOrgStructureByAddress(params)
            except WebFault, e:
                print e
            else:
                return result['list']
        else:
            raise exceptions.ValueError
        return None

    def getScheduleInfo(self, **kwargs):
        result = {}
        if kwargs['start'] and kwargs['end'] and kwargs['doctor_uid']:
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                start = (kwargs['start'] + i).strftime('%Y-%m-%d')
                params = {'serverId': kwargs['server_id'],
                          'personId': kwargs['doctor_uid'],
                          'date': start,
                          'hospitalUid': kwargs['hospital_uid_from'],
                          }
                result['timeslots'].extend(self.getWorkTimeAndStatus(**params))
        else:
            raise exceptions.ValueError
        return result

    def getWorkTimeAndStatus(self, **kwargs):
        try:
            schedule = self.client.service.getWorkTimeAndStatus(kwargs)
        except WebFault, e:
            print e
        else:
            result = []
            for key, timeslot in enumerate(schedule.amb.tickets):
                result.append({
                    'start': kwargs['date'] + 'T' + timeslot.time,
                    'finish': (
                        kwargs['date'] + 'T' + schedule.timeslots[key+1].time
                        if key < (len(schedule.timeslots) - 1)
                        else kwargs['date'] + 'T' + schedule.amb.endTime
                        ),
                    'status': 'free' if timeslot.status>0 else 'locked',
                    'office': schedule.amb.office,
                    'patientId': timeslot.patientId,
                    'patientInfo': timeslot.patientInfo,
                    })
            return result
        return []

    def getPatientQueue(self, **kwargs):
        if kwargs['serverId'] and kwargs['patientId']:
            params = {'serverId': kwargs['serverId'], 'patientId': kwargs['patientId'],}
            try:
                result = self.client.service.getPatientQueue(params)
            except WebFault, e:
                print e
            else:
                return result['list']
        else:
            raise exceptions.ValueError
        return None

    def getPatientInfo(self, **kwargs):
        if kwargs['serverId'] and kwargs['patientId']:
            params = {'serverId': kwargs['serverId'], 'patientId': kwargs['patientId'],}
            try:
                result = self.client.service.getPatientQueue(params)
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
                'serverId': kwargs['serverId'],
                'lastName': kwargs['person']['lastName'],
                'firstName': kwargs['person']['firstName'],
                'patrName': kwargs['person']['patronymic'],
                'omiPolicy': kwargs['omiPolicy'],
                'birthday': kwargs['birthday'],
                }
        except:
            raise exceptions.ValueError
        else:
            try:
                result = self.client.service.findPatient(params)
            except WebFault, e:
                print e
            else:
                return result
        return None

    def addPatient(self, **kwargs):
        try:
            params = {
                'serverId': kwargs['serverId'],
                'lastName': kwargs['person']['lastName'],
                'firstName': kwargs['person']['firstName'],
                'patrName': kwargs['person']['patronymic'],
#                'omiPolicy': kwargs['omiPolicy'],
                'birthday': kwargs['birthday'],
                }
        except:
            raise exceptions.ValueError
        else:
            try:
                result = self.client.service.addPatient(params)
            except WebFault, e:
                print e
            else:
                return result
        return None

    def enqueue(self, **kwargs):
        patient = self.findPatient(**kwargs)
        if (not patient or not patient.success) and kwargs['hospitalUidFrom']:
            patient = self.addPatient(**kwargs)

        if patient.patientId:
            patient_id = patient.patientId
        else:
            raise exceptions.LookupError
            return {'result': False, 'error_code': result.message,}

        try:
            date_time = kwargs['timeslotStart'].split('T')
            params = {
                'serverId': kwargs['serverId'],
                'patientId': patient_id,
                'personId': kwargs['doctorUid'],
                'date': date_time[0],
                'time': date_time[1],
                'note': kwargs['E-mail'],
                'hospitalUidFrom': kwargs['hospitalUidFrom'],
                }
        except:
            raise exceptions.ValueError
        else:
            try:
                result = self.client.service.enqueuePatient(params)
            except WebFault, e:
                print e
            else:
                if result.success:
                    return {
                        'result': True,
                        'error_code': result.message,
                        'ticketUid': result.queueId + '/' + patient_id,
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
                result = self.client.service.findOrgStructureByAddress(params)
                return result['list']
            except WebFault, e:
                print e
        else:
            raise exceptions.ValueError
        return result

    def getScheduleInfo(self, **kwargs):
        self.client = Client(self.url + 'egov.v3.queuePort.CLS?WSDL=1', cache=None)

        result = {}
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

        try:
            schedule = self.client.service.getScheduleInfo(params)
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

        if kwargs['serverId'] and kwargs['patientId']:
            params = {'serverId': kwargs['serverId'], 'patientId': kwargs['patientId'],}
            try:
                result = self.client.service.getPatientQueue(params)
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
                result = self.client.service.getPatientQueue(params)
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
                'person': kwargs['person'],
                'omiPolicyNumber': kwargs['omiPolicyNumber'],
                'birthday': kwargs['birthday'],
                'hospitalUid': kwargs['hospitalUid'],
                'speciality': kwargs['speciality'],
                'doctorUid': kwargs['doctorUid'],
                'timeslotStart': kwargs['timeslotStart'] + 'Z',
            }
        except:
            raise exceptions.ValueError
        else:
            try:
                result = self.client.service.enqueue(params)
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


class ClientCore(AbstractClient):
    def __init__(self, url):
        self.url = url

    def findOrgStructureByAddress(self):
        pass

    def getScheduleInfo(self):
        pass