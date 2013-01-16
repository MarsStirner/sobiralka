# coding: utf-8 -*-
from __builtin__ import classmethod

import logging
from spyne.application import Application
from spyne.protocol.soap import Soap11
from spyne.interface.wsdl.wsdl11 import Wsdl11
from spyne.util.simple import wsgi_soap_application
from spyne.server.wsgi import WsgiApplication
from spyne.util.wsgi_wrapper import WsgiMounter
from spyne.decorator import rpc
from spyne.service import ServiceBase
from spyne.protocol.http import HttpRpc
from spyne.model.primitive import NATIVE_MAP, Mandatory, AnyDict, String
from spyne.decorator import srpc, rpc
from spyne.model.complex import Array, Iterable, ComplexModel

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT, SOAP_NAMESPACE
from dataworker import DataWorker
import soap_models

class CustomWsgiMounter(WsgiMounter):
    """
    Customized WsgiMounter for bug fix of location address in wsdl:

    <wsdl:port name="Application" binding="tns:Application">
        <soap:address location="http://127.0.0.1:9900list"/>
    </wsdl:port>
    """

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '').rstrip('/') + '/'
        return super(CustomWsgiMounter, self).__call__(environ, start_response)


class InfoServer(ServiceBase):

    @srpc(soap_models.GetHospitalInfoRequest, _returns=soap_models.GetHospitalInfoResponse)
    def getHospitalInfo(HospitalInfoRequest):
        obj = DataWorker.provider('lpu')
        if HospitalInfoRequest:
            info = obj.get_info(**vars(HospitalInfoRequest))
        else:
            info = obj.get_info()
        return info

    def setDoctorInfo(self):
        pass

    def getHospitalUid(self):
        pass


class ListServer(ServiceBase):

    @srpc(soap_models.ListHospitalsRequest, _returns=soap_models.ListHospitalsResponse)
    def listHospitals(HospitalsRequest):
        obj = DataWorker.provider('lpu')
        if HospitalsRequest:
            hospitals = obj.get_list_hospitals(**vars(HospitalsRequest))
        else:
            hospitals = obj.get_list_hospitals()
        return hospitals

    @srpc(soap_models.ListDoctorsRequest, _returns=soap_models.ListDoctorsResponse)
    def listDoctors(DoctorsRequest):
        obj = DataWorker.provider('personal')
        if DoctorsRequest:
            doctors = obj.get_list_doctors(**vars(DoctorsRequest))
        else:
            doctors = obj.get_list_doctors()
        return doctors

    def listSpecialities(self):
        pass

    def listServTypesInfo(self):
        pass


class ScheduleServer(ServiceBase):

    @srpc(soap_models.GetScheduleInfoRequest, _returns=soap_models.GetScheduleInfoResponse)
    def getScheduleInfo(ScheduleInfoRequest):
        obj = DataWorker.provider('enqueue')
        return obj.get_info(**vars(ScheduleInfoRequest))

    @srpc(soap_models.GetTicketStatusRequest, _returns=soap_models.GetTicketStatusResponse)
    def getTicketStatus(TicketStatusRequest):
        obj = DataWorker.provider('enqueue')
        return obj.get_ticket_status(**vars(TicketStatusRequest))

    @srpc(soap_models.EnqueueRequest, _returns=soap_models.EnqueueResponse)
    def enqueue(EnqRequest):
        obj = DataWorker.provider('enqueue')
        return obj.enqueue(**vars(EnqRequest))

    def setTicketReadStatus(self):
        pass

    def cancel(self):
        pass

    def sendRequest(self):
        pass

    def listNewEnqueue(self):
        pass


class Server(object):

    @classmethod
    def run(cls):
        logging.basicConfig()
        from wsgiref.simple_server import make_server
        info = Application([InfoServer],
            tns=SOAP_NAMESPACE,
            name='InfoService',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        list = Application([ListServer],
            tns=SOAP_NAMESPACE,
            name='ListService',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        schedule = Application([ScheduleServer],
            tns=SOAP_NAMESPACE,
            name='ScheduleService',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        root = CustomWsgiMounter({
            'info': info,
            'list': list,
            'schedule': schedule,
            })

        server = make_server(SOAP_SERVER_HOST, SOAP_SERVER_PORT, root)
#        server = make_server(SOAP_SERVER_HOST, SOAP_SERVER_PORT, WsgiApplication(list))
        logging.info("listening to http://%s:%d" % (SOAP_SERVER_HOST, SOAP_SERVER_PORT))

        server.serve_forever()
