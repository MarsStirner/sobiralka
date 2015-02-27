# -*- coding: utf-8 -*-
try:
    import json
except ImportError:
    import simplejson as json
from ..service_clients import Clients
from ..dataworker import DataWorker
from ..utils import logger

logger_tags = dict(tags=['dataworker', 'IS'])


class ClientWorker(object):
    """Класс для работы с информацией по пациентам"""

    def get_patient(self, hospital_uid, patient_id):
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        if isinstance(hospital_uid, list) and len(hospital_uid) > 1:
            lpu_dw = DataWorker.provider('lpu')
            lpu = lpu_dw.get_by_id(hospital_uid[0])
        else:
            logger.error(ValueError(), extra=logger_tags)
            return None
        try:
            proxy_client = Clients.provider(lpu.protocol, lpu.proxy.split(';')[0])
            result = proxy_client.getPatientInfo(patientId=patient_id)
        except Exception, e:
            logger.error(e, extra=logger_tags)
            return None
        else:
            return result