# -*- coding: utf-8 -*-

import unittest
import logging
import datetime
from int_service.lib.service_clients import ClientEPGU

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)

client = ClientEPGU()


class ClientTests(unittest.TestCase):

    def test_GetMedicalSpecializations(self):
        res = client.GetMedicalSpecializations('CKzeDG37SdTRjzddVCn6')
        self.assertIsInstance(res['medical-specialization'], list)

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
        res = client.GetReservationTypes('CKzeDG37SdTRjzddVCn6')
        self.assertIsInstance(res['reservation-type'], list)
        self.assertListEqual(res['reservation-type'], assert_result)

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
        res = client.GetPaymentMethods(auth_token='CKzeDG37SdTRjzddVCn6')
        self.assertIsInstance(res['payment-method'], list)
        self.assertListEqual(res['payment-method'], assert_result)

    def test_GetServiceTypes(self):
        res = client.GetServiceTypes('CKzeDG37SdTRjzddVCn6')
        self.assertIsInstance(res['service-type'], list)

    def test_GetServiceType(self):
        res = client.GetServiceType('CKzeDG37SdTRjzddVCn6', '4f882b9c2bcfa5145a0006e8')
        self.assertIsInstance(res, dict)

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
        hospital = {'place_id': '4f1e8fa0c95ea177b00000b6', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.DeleteEditLocation(hospital, '4f9bb3f92bcfa5314d000070')
        self.assertIsInstance(res, list)

    def test_PostLocations(self):
        doctor = {'prefix': u'ФИО врача',
                  'medical_specialization_id': '4f882b982bcfa5145a00039a',
                  'cabinet_number': '13',
                  'time_table_period': '15',
                  'reservation_time': '1',
                  'reserved_time_for_slot': '1',
                  'reservation_type_id': '4f8805b52bcfa52299000012',
                  'payment_method_id': '4f8804ab2bcfa520e6000001'}
        service_types = ['4f882b9c2bcfa5145a0006f6']
        hospital = {'place_id': '4f1e8fa0c95ea177b00000b6', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.PostLocations(hospital, doctor, service_types)
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
        hospital = {'place_id': '4f27ecd72bcfa52a560000a5', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.PostRules(hospital, doctor, period, days)
        self.assertIsInstance(res, dict)

    def test_PutLocationSchedule(self):
        location_id = '4f8840a62bcfa54a0f002fe8'
        rules = [{'id': '50507480ef2455c01202a0ca',
                 'start': (datetime.datetime.today() -
                           datetime.timedelta(days=datetime.datetime.today().isoweekday() + 1)),
                 'end': (datetime.datetime.today() +
                         datetime.timedelta(days=(7 - datetime.datetime.today().isoweekday())))
                  }, ]
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.PutLocationSchedule(hospital, location_id, rules)
        self.assertIsInstance(res, dict)

    def test_PutActivateLocation(self):
        location_id = '4f9bb3f92bcfa5314d000070'
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        res = client.PutActivateLocation(hospital, location_id)
        self.assertIsInstance(res, dict)

    def test_PostReserve(self):
        doctor_id = '4f28f1f2c95ea12bbc0002a6'
        service_type_id = '4f28e642c95ea12358000005'
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CmBPwiTZhiePQQZMu5iL'}
        date = {'date': datetime.datetime.today().date(), 'start_time': '08:30'}
        res = client.PostReserve(hospital, doctor_id, service_type_id, date)
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
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CKzeDG37SdTRjzddVCn6'}
        res = client.PutSlot(hospital, patient, slot_id)
        self.assertIsInstance(res, dict)

    def test_DeleteSlot(self):
        slot_id = '4f33b7b72bcfa52ddd000470'
        hospital = {'place_id': '4f880ca42bcfa5277202f051', 'auth_token': 'CKzeDG37SdTRjzddVCn6'}
        res = client.DeleteSlot(hospital, slot_id)
        self.assertIsInstance(res, dict)


if __name__ == '__main__':
    unittest.main()
