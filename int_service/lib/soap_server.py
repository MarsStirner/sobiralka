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
import version


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

    @srpc(soap_models.GetHospitalInfoRequest, _returns=soap_models.GetHospitalInfoResponse, _out_variable_name='info')
    def getHospitalInfo(parameters):
        obj = DataWorker.provider('lpu')
        if parameters:
            info = obj.get_info(**vars(parameters))
        else:
            info = obj.get_info()
        return info

    def setDoctorInfo(self):
        pass

    @srpc(soap_models.GetHospitalUidRequest, _returns=soap_models.GetHospitalUidResponse)
    def getHospitalUid(parameters):
        obj = DataWorker.provider('lpu')
        return obj.get_uid_by_code(code=parameters.hospitalCode)

    @rpc(_returns=soap_models.GetVersionResponse)
    def getVersion(self):
        return {'version': version.version, 'last_update': version.last_change_date}


class ListServer(ServiceBase):

    @rpc(_returns=soap_models.ListRegionsResponse)
    def listRegions(self):
        obj = DataWorker.provider('regions')
        return {'regions': obj.get_list()}

    @srpc(soap_models.ListHospitalsRequest, _returns=soap_models.ListHospitalsResponse, _out_variable_name='hospitals')
    def listHospitals(parameters):
        obj = DataWorker.provider('lpu')
        if parameters:
            hospitals = obj.get_list_hospitals(**vars(parameters))
        else:
            hospitals = obj.get_list_hospitals()
        return hospitals

    @srpc(soap_models.ListDoctorsRequest, _returns=soap_models.ListDoctorsResponse, _out_variable_name='doctors')
    def listDoctors(parameters):
        obj = DataWorker.provider('personal')
        if parameters:
            doctors = obj.get_list_doctors(**vars(parameters))
        else:
            doctors = obj.get_list_doctors()
        return doctors

    @srpc(soap_models.ListSpecialitiesRequest,
          _returns=soap_models.ListSpecialitiesResponse,
          _out_variable_name='speciality')
    def listSpecialities(parameters):
        obj = DataWorker.provider('personal')
        return obj.get_list_specialities(**vars(parameters))

    def listServTypesInfo(self):
        pass


class ScheduleServer(ServiceBase):

    @srpc(soap_models.GetScheduleInfoRequest,
          _returns=soap_models.GetScheduleInfoResponse,
          _out_variable_name='timeslots')
    def getScheduleInfo(parameters):
        obj = DataWorker.provider('enqueue')
        return obj.get_info(**vars(parameters))

    @srpc(soap_models.GetTicketStatusRequest, _returns=soap_models.GetTicketStatusResponse)
    def getTicketStatus(parameters):
        obj = DataWorker.provider('enqueue')
        return obj.get_ticket_status(**vars(parameters))

    @srpc(soap_models.EnqueueRequest, _returns=soap_models.EnqueueResponse)
    def enqueue(parameters):
        obj = DataWorker.provider('enqueue')
        return obj.enqueue(**vars(parameters))

    def setTicketReadStatus(self):
        pass

    def cancel(self):
        pass

    def sendRequest(self):
        pass

    def listNewEnqueue(self):
        pass


class Server(object):

    def __init__(self):
        logging.basicConfig()
        info_app = Application(
            [InfoServer],
            tns=SOAP_NAMESPACE,
            name='InfoService',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        list_app = Application(
            [ListServer],
            tns=SOAP_NAMESPACE,
            name='ListService',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        schedule_app = Application(
            [ScheduleServer],
            tns=SOAP_NAMESPACE,
            name='ScheduleService',
            interface=Wsdl11(),
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        self.applications = CustomWsgiMounter({
            'info': info_app,
            'list': list_app,
            'schedule': schedule_app,
        })

    def run(self):
        from wsgiref.simple_server import make_server
        server = make_server(SOAP_SERVER_HOST, SOAP_SERVER_PORT, self.applications)
        logging.info("listening to http://%s:%d" % (SOAP_SERVER_HOST, SOAP_SERVER_PORT))
        server.serve_forever()
