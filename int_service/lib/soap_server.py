# coding: utf-8 -*-
from __builtin__ import classmethod

import logging
from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.interface.wsdl.wsdl11 import Wsdl11
from spyne.util.simple import wsgi_soap_application
from spyne.util.wsgi_wrapper import WsgiMounter
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.protocol.http import HttpRpc
from spyne.model.primitive import NATIVE_MAP, Mandatory, AnyDict
from spyne.decorator import srpc, rpc
from spyne.model.complex import Array, Iterable, ComplexModel

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT
from dataworker import DataWorker
import soap_models

class InfoServer(ServiceBase):

    @rpc(soap_models.GetHospitalInfoRequest, _returns=soap_models.GetHospitalInfoResponse)
    def getHospitalInfo(self, **kwargs):
        obj = DataWorker.provider('lpu')
        return obj.get_info(**kwargs)

    def setDoctorInfo(self):
        pass

    def getHospitalUid(self):
        pass


class ListServer(ServiceBase):

    @rpc(soap_models.ListHospitalsRequest, _returns=soap_models.ListHospitalsResponse)
    def listHospitals(self, **kwargs):
        obj = DataWorker.provider('lpu')
        return obj.get_list_hospitals(**kwargs)

    @rpc(soap_models.ListDoctorsRequest, _returns=soap_models.ListDoctorsResponse)
    def listDoctors(self, **kwargs):
        obj = DataWorker.provider('personal')
        return obj.get_list_doctors(**kwargs)

    def listSpecialities(self):
        pass

    def listServTypesInfo(self):
        pass


class ScheduleServer(ServiceBase):

    @rpc(soap_models.GetScheduleInfoRequest, _returns=soap_models.GetScheduleInfoResponse)
    def getScheduleInfo(self, **kwargs):
        obj = DataWorker.provider('enqueue')
        return obj.get_info(**kwargs)

    @rpc(soap_models.GetTicketStatusRequest, _returns=soap_models.GetTicketStatusResponse)
    def getTicketStatus(self, **kwargs):
        obj = DataWorker.provider('enqueue')
        return obj.get_ticket_status(**kwargs)

    @rpc(soap_models.EnqueueRequest, _returns=soap_models.EnqueueResponse)
    def enqueue(self):
        obj = DataWorker.provider('enqueue')
        return obj.enqueue(**kwargs)

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
        info = Application([InfoServer],
            'urn:ru.gov.economy:std.ws',
            name='HospitalInfo',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        list = Application([ListServer],
            'tns',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        schedule = Application([ScheduleServer],
            'tns',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        root = WsgiMounter({
            'info': info,
            'list': list,
            'schedule': schedule,
            })

        server = make_server(SOAP_SERVER_HOST, SOAP_SERVER_PORT, root)
        logging.basicConfig(level=logging.DEBUG)
        logging.info("listening to http://%s:%d" % (SOAP_SERVER_HOST, SOAP_SERVER_PORT))

        server.serve_forever()
