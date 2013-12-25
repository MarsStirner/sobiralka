# -*- coding: utf-8 -*-
import exceptions
import logging
import settings
from clients.epgu import ClientEPGU
from clients.korus20 import ClientKorus20
from clients.korus30 import ClientKorus30, CouponStatus
from clients.intramed import ClientIntramed


class Clients(object):
    """Class provider for current Clients"""
    @classmethod
    def provider(cls, client_type, proxy_url):
        logging.basicConfig(level=logging.ERROR)
        if settings.DEBUG:
            logging.getLogger('suds.client').setLevel(logging.ERROR)
            logging.getLogger('Thrift_Client').setLevel(logging.DEBUG)
        else:
            logging.getLogger('suds.client').setLevel(logging.CRITICAL)
            logging.getLogger('Thrift_Client').setLevel(logging.CRITICAL)

        client_type = client_type.lower()
        if client_type in ('samson', 'korus20'):
            obj = ClientKorus20(proxy_url)
        elif client_type == 'intramed':
            obj = ClientIntramed(proxy_url)
        elif client_type in ('core', 'korus30'):
            obj = ClientKorus30(proxy_url)
        else:
            obj = None
            raise exceptions.NameError
        return obj