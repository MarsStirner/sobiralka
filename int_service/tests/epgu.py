# -*- coding: utf-8 -*-

import unittest
import logging
import datetime
from int_service.lib.service_clients import ClientEPGU

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)

client = ClientEPGU()


class ClientTests(unittest.TestCase):

    def test_GetMedicalSpecialization(self):
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
        res = client.GetPaymentMethods()
        self.assertIsInstance(res, list)
        self.assertListEqual(res, assert_result)

    def test_GetServiceType(self):
        res = client.GetServiceType()
        self.assertIsInstance(res, list)

    def test_GetPlace(self):
        assert_result = {'id': '4f880ca42bcfa5277202f051',
                         'name': u'ГУЗ "ПЕНЗЕНСКАЯ ОБЛАСТНАЯ КЛИНИЧЕСКАЯ БОЛЬНИЦА ИМ.Н.Н.БУРДЕНКО"'}
        res = client.GetPlace(auth_token='CKzeDG37SdTRjzddVCn6')
        self.assertIsInstance(res, dict)
        self.assertDictEqual(res, assert_result)

    def test_GetLocations(self):
        hospital = {'place_id': '4f1e8fa0c95ea177b00000b6', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.GetLocations(service_type_id='4f1e8fa0c95ea177b00000b3',
                                  hospital=hospital)
        self.assertIsInstance(res, list)

    def test_DeleteEditLocation(self):
        pass

    def test_PostLocations(self):
        doctor = {'prefix': u'ФИО врача',
                  'medical_specialization_id': '4f882b982bcfa5145a000383',
                  'cabinet_number': '13',
                  'time_table_period': '15',
                  'reservation_time': '1',
                  'reserved_time_for_slot': '1',
                  'reservation_type_id': '4f8805b52bcfa52299000011',
                  'payment_method_id': '4f8804ab2bcfa520e6000001'}
        service_types = ['4f882b9c2bcfa5145a0006e8']
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CKzeDG37SdTRjzddVCn6'}
        res = client.PostLocations(doctor, service_types, hospital)
        self.assertIsInstance(res, dict)

    def test_PostRules(self):
        doctor = u'ФИО врача'
        period = '%s - %s' % (
            (
                datetime.datetime.today() - datetime.timedelta(days=datetime.datetime.today().isoweekday() + 1)
            ).strftime('%d.%m.%Y'),
            (
                datetime.datetime.today() + datetime.timedelta(days=(7 - datetime.datetime.today().isoweekday()))
            ).strftime('%d.%m.%Y'),
        )
        days = [dict(date=datetime.datetime.today(), start='08:00', end='18:00')]
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CKzeDG37SdTRjzddVCn6'}
        res = client.PostRules(doctor, period, days, hospital)
        self.assertIsInstance(res, dict)

    def test_PostLocationSchedule(self):
        doctor_id = '50506af8bb4d3371b8028ea3'
        rule = {'id': '50507480ef2455c01202a0ca',
                'start': (datetime.datetime.today() -
                          datetime.timedelta(days=datetime.datetime.today().isoweekday() + 1)),
                'end': (datetime.datetime.today() +
                        datetime.timedelta(days=(7 - datetime.datetime.today().isoweekday())))
                }
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CKzeDG37SdTRjzddVCn6'}
        res = client.PostLocationSchedule(doctor_id, rule, hospital)
        self.assertIsInstance(res, dict)

    def test_PutActivateLocation(self):
        doctor_id = '50506af8bb4d3371b8028ea3'
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CKzeDG37SdTRjzddVCn6'}
        res = client.PutActivateLocation(doctor_id, hospital)
        self.assertIsInstance(res, dict)

    def test_PostReserve(self):
        doctor_id = '4f28f1f2c95ea12bbc0002a6'
        service_type_id = '4f28e642c95ea12358000005'
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        date = {'date': datetime.datetime.today().date(), 'start_time': '08:30'}
        res = client.PostReserve(doctor_id, hospital, service_type_id, date)
        self.assertIsInstance(res, dict)

    def test_PutSlot(self):
        patient = {
            'name': u'Имя',
            'surname': u'Фамилия',
            'patronymic': u'Отчество',
            'phone': '+7(472)3515909',
            'id': '240721313',
        }
        slot_id = '32ghghgjhg43hjh5ghghdfHGDHSdhg34h3g5h4g5h4'
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.PutSlot(patient, hospital, slot_id)
        self.assertIsInstance(res, dict)

    def test_DeleteSlot(self):
        slot_id = '4f33b7b72bcfa52ddd000470'
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.DeleteSlot(slot_id, hospital)
        self.assertIsInstance(res, dict)


if __name__ == '__main__':
    unittest.main()
