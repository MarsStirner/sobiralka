# -*- coding: utf-8 -*-
import requests
from flask import json
from datetime import datetime

import logging
import sys
from utils import logger

h1 = logging.StreamHandler(sys.stdout)
rootLogger = logging.getLogger()
rootLogger.addHandler(h1)
tfoms_logger = logging.getLogger("tfoms.logger")
tfoms_logger.addHandler(h1)
tfoms_logger.setLevel(logging.DEBUG)

_codes = {
    0: u'Ошибка при работе с сервисом',
    1: u'По переданным данным пациент не найден в БД ТФОМС',
    2: u'Пациент найден в БД ТФОМС',
    3: u'Полис найден, несовпадение даты рождения'
}

logger_tags = dict(tags=['tfoms_client', 'IS', __file__])


class AnswerCodes(object):
    code = None
    message = None

    def __init__(self, code):
        if code not in _codes:
            code = 0
        self.code = code
        self.message = _codes[code]


class TFOMSClient(object):

    def __init__(self, host, port, login, password):
        self.service_url = 'http://{host}:{port}'.format(host=host, port=port)
        self.__is_available = False
        self.__is_logined = False
        self.cookies = None
        self.__check_service()
        if self.is_available:
            self.is_logined = self.__login(login, password)

    @property
    def is_available(self):
        return self.__is_available

    @is_available.setter
    def is_available(self, value):
        self.__is_available = value

    @property
    def is_logined(self):
        return self.__is_logined

    @is_logined.setter
    def is_logined(self, value):
        self.__is_logined = value

    def __check_service(self):
        tfoms_logger.debug('CHECK TFOMS_SERVICE')
        try:
            r = requests.get(self.service_url, timeout=0.5)
        except requests.Timeout, e:
            tfoms_logger.debug(e)
            logger.error(e, extra=logger_tags)
            print e
            self.is_available = False
            tfoms_logger.debug('CHECK FAILED')
        else:
            tfoms_logger.debug('CHECK SUCCESS')
            self.is_available = True

    def __login(self, login, password):
        tfoms_logger.debug('LOGIN TFOMS_SERVICE (%s, %s)' % (login, password))
        url = '{}/login'.format(self.service_url)
        r = requests.post(url, data=json.dumps(dict(login=login, password=password)))
        if r.status_code == requests.codes.ok:
            tfoms_logger.debug('LOGIN SUCCESS')
            if r.cookies['session']:
                tfoms_logger.debug(r.cookies['session'])
                self.cookies = dict(session=r.cookies['session'])
            return True
        elif r.status_code == requests.codes.unauthorized:
            tfoms_logger.debug('LOGIN FAILED')
            return False
        tfoms_logger.debug('LOGIN FAILED')
        return False

    def __check(self, **kwargs):
        if self.is_logined:
            url = '{}/check'.format(self.service_url)
            r = requests.post(url, data=json.dumps(kwargs), cookies=self.cookies)
            if r.status_code == requests.codes.ok:
                if r.content == 'true':
                    return True
                elif r.content == 'false':
                    return False
        return None

    def __search(self, **kwargs):
        tfoms_logger.debug('SEARCH PROCESS')
        if self.is_logined:
            url = '{}/search'.format(self.service_url)
            r = requests.post(url, data=json.dumps(kwargs), cookies=self.cookies)
            tfoms_logger.debug(self.cookies)
            if r.status_code == requests.codes.ok:
                try:
                    result = r.json()
                    tfoms_logger.debug(result)
                except ValueError, e:
                    tfoms_logger.error(e)
                    logger.error(e, extra=logger_tags)
                    raise e
                else:
                    return result
        tfoms_logger.debug('NOT LOGINED')
        return None

    def check_policy(self, policy):
        return self.__check(**policy)

    def search_policy(self, policy):
        return self.__search(**policy)

    def __get_policy_data(self, data):
        policy = dict()
        if 'policy_type' not in data:
            raise AttributeError
        policy['policy_doctype'] = int(data['policy_type'])
        if 'serial' in data:
            policy['policy_series'] = data['serial']
        elif 'series' in data:
            policy['policy_series'] = data['series']
        policy['policy_number'] = data['number']
        return policy

    def __get_patient_data(self, data):
        patient = dict()
        if 'birthDate' in data:
            patient['birthdate'] = datetime.strftime(data['birthDate'], '%d.%m.%Y')
        return patient

    def search_patient(self, patient_data):
        try:
            policy = self.__get_policy_data(patient_data)
            patient = self.__get_patient_data(patient_data)
        except AttributeError, e:
            logger.error(e, extra=logger_tags)
            return dict(status=AnswerCodes(0), data=None)

        all_data = patient
        all_data.update(policy)
        try:
            result = self.__search(**all_data)
        except ValueError, e:
            print e
            logger.error(e, extra=logger_tags)
            return dict(status=AnswerCodes(0), data=None)
        if result:
            return dict(status=AnswerCodes(2), data=result)
        elif result is None:
            return dict(status=AnswerCodes(0), data=None)
        else:
            # Не нашли пациента в ТФОМС, проверяем только полис
            try:
                result = self.__search(**policy)
            except ValueError, e:
                print e
                logger.error(e, extra=logger_tags)
                return dict(status=AnswerCodes(0), data=None)
            if result:
                return dict(status=AnswerCodes(3), data=result)
            elif result is None:
                return dict(status=AnswerCodes(0), data=None)
            else:
                return dict(status=AnswerCodes(1), data=None)