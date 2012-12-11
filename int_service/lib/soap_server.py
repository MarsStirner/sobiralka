# coding: utf-8 -*-
from __builtin__ import classmethod

import logging
from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.util.simple import wsgi_soap_application
from spyne.util.wsgi_wrapper import WsgiMounter

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT
from dataworker import DataWorker

class InfoServer(object):

    def getHospitalInfo(self, **kwargs):
        obj = DataWorker.provider('lpu')
        return obj.get_info(kwargs)

    def setDoctorInfo(self):
        pass

    def getHospitalUid(self):
        pass


class ListServer(object):

    def listHospitals(self, **kwargs):
        obj = DataWorker.provider('lpu')
        return obj.get_list_hospitals(**kwargs)

    def listDoctors(self, **kwargs):
        obj = DataWorker.provider('personal')
        return obj.get_list_doctors(kwargs)

    def listSpecialities(self):
        pass

    def listServTypesInfo(self):
        pass


class ScheduleServer(object):

    def getScheduleInfo(self, **kwargs):
        obj = DataWorker.provider('enqueue')
        return obj.get_info(kwargs)

    def getTicketStatus(self, **kwargs):
        obj = DataWorker.provider('enqueue')
        return obj.get_ticket_status(**kwargs)

    def enqueue(self):
        pass

    def setTicketReadStatus(self):
        pass

    def cancel(self):
        pass

    def getTicketStatus(self):
        pass

    def sendRequest(self):
        pass

    def listNewEnqueue(self):
        pass


class Server(object):

    @classmethod
    def run(cls):
        from wsgiref.simple_server import make_server
        root = WsgiMounter({
            'info': InfoServer(),
            'list': ListServer(),
            'schedule': ScheduleServer(),
            })

        server = make_server(SOAP_SERVER_HOST, SOAP_SERVER_PORT, root)
        logging.basicConfig(level=logging.DEBUG)
        logging.info("listening to http://%s:%d" % (SOAP_SERVER_HOST, SOAP_SERVER_PORT))

        server.serve_forever()
