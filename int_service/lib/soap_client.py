# -*- coding: utf-8 -*-

import exceptions
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


class ClientCore(ProxyCAbstractClientlient):
    def __init__(self, url):
        self.url = url

    def findOrgStructureByAddress(self):
        pass