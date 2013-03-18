# -*- coding: utf-8 -*-

import unittest
import logging
from suds.client import Client
from int_service.lib.service_clients import ClientEPGU

logging.basicConfig()
logging.getLogger('suds.client').setLevel(logging.DEBUG)


class ClientTests(unittest.TestCase):

    def test_GetMedicalSpecialization(self):
        client = ClientEPGU()
        res = client.GetMedicalSpecialization()
        self.assertIsInstance(res, list)

    def test_GetReservationTypes(self):
        assert_result = [{'id': "4f8805b52bcfa52299000011",
                          'name': u"Автоматическая запись",
                          'code': "automatic",
                          },
                         {'id': "4f8805b52bcfa52299000013",
                          'name': u"Запись по листу ожидания",
                          'code': "waiting_list",
                          },
                         {'id': "4f8805b52bcfa52299000012",
                          'name': u"Запись с подтверждением",
                          'code': "manual",
                          }, ]
        client = ClientEPGU()
        res = client.GetReservationTypes()
        self.assertIsInstance(res, list)
        self.assertListEqual(res, assert_result)

    def test_GetPaymentMethods(self):
        assert_result = [{'id': "4f8804ab2bcfa520e6000003",
                          'name': u"Бюджетные пациенты",
                          'default': "",
                          },
                         {'id': "4f8804ab2bcfa520e6000002",
                          'name': u"Пациенты ДМС",
                          'default': "",
                          },
                         {'id': "4f8804ab2bcfa520e6000001",
                          'name': u"Пациенты с полисами ОМС",
                          'default': "true",
                          }, ]
        client = ClientEPGU()
        res = client.GetPaymentMethods()
        self.assertIsInstance(res, list)
        self.assertListEqual(res, assert_result)

    def test_GetServiceType(self):
        client = ClientEPGU()
        res = client.GetServiceType()
        self.assertIsInstance(res, list)

    def test_GetPlace(self):
        assert_result = {'id': '4f880ca42bcfa5277202f051',
                         'name': u'ГУЗ "ПЕНЗЕНСКАЯ ОБЛАСТНАЯ КЛИНИЧЕСКАЯ БОЛЬНИЦА ИМ.Н.Н.БУРДЕНКО"'}
        client = ClientEPGU()
        res = client.GetPlace(auth_token='CKzeDG37SdTRjzddVCn6')
        self.assertIsInstance(res, dict)
        self.assertDictEqual(res, assert_result)

    def test_GetLocations(self):
        client = ClientEPGU()
        res = client.GetLocations(place_id='4f1e8fa0c95ea177b00000b6',
                                  service_type_id='4f1e8fa0c95ea177b00000b3',
                                  auth_token='CmBPwiTZhiePQQZMu5iL')
        self.assertIsInstance(res, dict)


if __name__ == '__main__':
    unittest.main()
