# -*- coding: utf-8 -*-

import exceptions
import datetime
from abc import ABCMeta, abstractmethod, abstractproperty
from suds.client import Client

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

class ClientSamson(AbstractClient):
    def __init__(self, url):
        self.client = Client(url)

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
        result = {}
        if kwargs['start'] and kwargs['end'] and kwargs['doctor_uid']:
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                start = (kwargs['start'] + i).strftime('%Y-%m-%d')
                params = {'serverId': kwargs['server_id'],
                          'personId': kwargs['doctor_uid'],
                          'date': start,
                          'hospitalUid': kwargs['hospital_uid_from'],
                          }
                try:
                    schedule = self.client.service.getWorkTimeAndStatus(params)
                except WebFault, e:
                    print e
                else:
                    for key, timeslot in enumerate(schedule.timeslots):
                        result['timeslots'].append({
                            'start': start + 'T' + timeslot.time,
                            'finish': (start + 'T' + schedule.timeslots[key+1].time
                                       if key < (len(schedule.timeslots) - 1)
                                       else start + 'T' + timeslot.amb.endTime),
                            'status': 'free' if timeslot.status>0 else 'locked',
                            'office': timeslot.amb.office,
                            'patientId': timeslot.patientId,
                            'patientInfo': timeslot.patientInfo,
                            })
        else:
            raise exceptions.ValueError

        return result


class ClientIntramed(AbstractClient):
    def __init__(self, url):
        self.url = url

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
        result = {}
        if kwargs['start'] and kwargs['end'] and kwargs['doctor_uid'] and kwargs['hospital_uid']:
            for i in xrange((kwargs['end'] - kwargs['start']).days):
                params = {'doctorUid': kwargs['doctor_uid'],
                          'speciality': kwargs['speciality'],
                          'startDate': (kwargs['start'] + i).strftime('%Y-%m-%d'),
                          'hospitalUid': kwargs['hospital_uid'][1],
                          }
                try:
                    schedule = self.client.service.getScheduleInfo(params)
                except WebFault, e:
                    print e
                else:
                    for key, timeslot in enumerate(schedule.timeslots):
                        result['timeslots'].append({
                            'start': timeslot.start,
                            'finish': (schedule.timeslots[key+1].start
                                       if key < (len(schedule.timeslots) - 1)
                                       else schedule.finish),
                            'status': timeslot.status,
                            'office': '0',
                            })
        else:
            raise exceptions.ValueError

        return result


class ClientCore(ProxyCAbstractClientlient):
    def __init__(self, url):
        self.url = url

    def findOrgStructureByAddress(self):
        pass

    def getScheduleInfo(self):
        pass