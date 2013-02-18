# -*- coding: utf-8 -*-
import os
import datetime
import main
import unittest
import logging
from suds.client import Client
from int_service.lib import soap_models
from int_service.lib.service_clients import ClientKorus30

logging.basicConfig()
logging.getLogger('suds.client').setLevel(logging.DEBUG)

IS = "http://127.0.0.1:9910/%s/?wsdl"
# IS = "http://10.1.2.107:9910/%s/?wsdl"


class TestListWSDL(unittest.TestCase):
    client = Client(IS % "list", cache=None)

    def testListRegions(self):
        regions = self.client.listRegions()
        self.assertIsInstance(regions.regions, list)

    def testListHospitalsKorus20_0(self):
        okato = "56401000000"
        result = [ {'uid': "5/0",
                    'title': u"ГБУЗ «Пензенская областная клиническая больница им. Н.Н. Бурденко»",
                    'phone': "8412(32-03-57)",
                    'address': u"г. Пенза, ул. Лермонтова, 28",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580063"
                   },
                   {'uid': "17/0",
                    'title': u"ГБУЗ «Пензенская областная детская клиническая больница им. Н. Ф. Филатова»",
                    'phone': "(8412) 42-75-73",
                    'address': u"Пензенская область, Городищенский район, улица Бекешская, 43",
                    'wsdlURL': IS + "schedule",
                    'token': "G5xFjT9ggLDwZCyPpnqx",
                    'key': "580064"
                   },
                   ]
        hospitals = self.client.service.listHospitals({'ocatoCode': okato})
        self.assertIsInstance(hospitals.hospitals, list)
        self.assertEqual(hospitals.hospitals, result)

    def testListHospitalsKorus20_1(self):
        okato = "56405000000"
        result = [ {'uid': "11/0",
                    'name': u"ГБУЗ «Кузнецкая ЦРБ»",
                    'phone': "(841-57) 2-05-99",
                    'address': u"Пензенская обл., г. Кузнецк, ул. Сызранская, 142",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580033"
                   },]
        hospitals = self.client.service.listHospitals({'ocatoCode': okato})
        self.assertIsInstance(hospitals.hospitals, list)
        self.assertListEqual(hospitals.hospitals, result)

    def testListHospitalsKorus30(self):
        okato = "45293578000"
#        result = [ {'uid': "11/0",
#                    'title': u"ГБУЗ «Кузнецкая ЦРБ»",
#                    'phone': "(841-57) 2-05-99",
#                    'address': u"Пензенская обл., г. Кузнецк, ул. Сызранская, 142",
#                    'wsdlURL': IS + "schedule",
#                    'token': "None",
#                    'key': "580033"
#                   },]
        hospitals = self.client.service.listHospitals({'ocatoCode': okato})
        self.assertIsInstance(hospitals.hospitals, list)
#        self.assertListEqual(list(hospitals), result)

    def testListHospitalsKorus20_2(self):
        okato = "56203000000"
        result = [{
            'key': "580016",
            'uid': "28/0",
            'phone': "(841-43)4-11-70",
            'token': "fUvLysu6qGfAVYdHyyJm",
            'wsdlURL': "http://127.0.0.1:9910/schedule/?wsdl",
            ' address': "Пензенская обл., р.п. Башмаково, ул. Строителей, 22",
            'name': "ГБУЗ «Башмаковская ЦРБ»"
        }]
        hospitals = self.client.service.listHospitals({'ocatoCode': okato})
        self.assertIsInstance(hospitals.hospitals, list)
        self.assertListEqual(hospitals.hospitals, result)

    def testListHospitalsKorus20_3(self):
        result = [ {'uid': "5/0",
                    'title': u"ГБУЗ «Пензенская областная клиническая больница им. Н.Н. Бурденко»",
                    'phone': "8412(32-03-57)",
                    'address': u"г. Пенза, ул. Лермонтова, 28",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580063"
                   },
                   {'uid': "17/0",
                    'title': u"ГБУЗ «Пензенская областная детская клиническая больница им. Н. Ф. Филатова»",
                    'phone': "(8412) 42-75-73",
                    'address': u"Пензенская область, Городищенский район, улица Бекешская, 43",
                    'wsdlURL': IS + "schedule",
                    'token': "G5xFjT9ggLDwZCyPpnqx",
                    'key': "580064"
                   },
                   {'uid': "11/0",
                    'title': u"ГБУЗ «Кузнецкая ЦРБ»",
                    'phone': "(841-57) 2-05-99",
                    'address': u"Пензенская обл., г. Кузнецк, ул. Сызранская, 142",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580033"
                   },
                   {'uid': "5/108/0",
                    'title': u"Главные специалисты МЗ и СР ПО",
                    'phone': "8412(32-03-57)",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580063"
                   },
                   {'uid': "5/65/0",
                    'title': u"Диабетологический центр",
                    'phone': "8412(32-03-57)",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580063"
                   },
                   {'uid': "5/64/0",
                    'title': u"Кардиологический диспансер",
                    'phone': "8412(32-03-57)",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580063"
                   },
                   {'uid': "5/110/0",
                    'title': u"Профпатологический центр",
                    'phone': "8412(32-03-57)",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580063"
                   },
                   {'uid': "5/104/0",
                    'title': u"Эндоскопическое отделение",
                    'phone': "8412(32-03-57)",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580063"
                   },
                   {'uid': "17/52/0",
                    'title': u"Поликлиника консультативно-диагностическая №1 (для детей)",
                    'phone': "(8412) 42-75-73",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "G5xFjT9ggLDwZCyPpnqx",
                    'key': "580064"
                   },
                   {'uid': "17/53/0",
                    'title': u"Поликлиника консультативно-диагностическая №2 (для женщин)",
                    'phone': "(8412) 42-75-73",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "G5xFjT9ggLDwZCyPpnqx",
                    'key': "580064"
                   },
                   {'uid': "17/54/0",
                    'title': u"Центр планирования семьи и репродукции",
                    'phone': "(8412) 42-75-73",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "G5xFjT9ggLDwZCyPpnqx",
                    'key': "580064"
                   },
                   {'uid': "11/1025801446528/0",
                    'title': u'ОБУЗ "ОБЛАСТНОЙ ПЕРИНАТАЛЬНЫЙ ЦЕНТР"',
                    'phone': "(841-57) 2-05-99",
                    'address': "None",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580033"
                   },
                   ]
        hospitals = self.client.service.listHospitals()
        self.assertIsInstance(hospitals.hospitals, list)
        self.assertListEqual(hospitals.hospitals, result)

    def testListHospitalsKorus20_4(self):
        okato = "11111111"
        result = []
        hospitals = self.client.service.listHospitals({'ocatoCode': okato})
        if hospitals:
            self.assertIsInstance(hospitals.hospitals, soap_models.ListHospitalsResponse)
            self.assertListEqual(hospitals.hospitals, result)

    def testListHospitalsIntramed(self):
        okato = "580033"
        result = []
        hospitals = self.client.service.listHospitals({'ocatoCode': okato})
        if hospitals:
            self.assertIsInstance(hospitals.hospitals, soap_models.ListHospitalsResponse)
            self.assertListEqual(hospitals.hospitals, result)

    def testFindOrgStructureByAddressKorus30(self):
        client = ClientKorus30('http://10.2.1.58:7911')
        hospitals = client.findOrgStructureByAddress(
            pointKLADR = '4800000100000',
            streetKLADR = '48000001000030800',
            number = '43',
            flat = 0
        )
        self.assertIsInstance(hospitals, list)

    def testListDoctorsKorus20(self):
        hospital_Uid = '17/52'
        speciality = u"Акушер-гинеколог (лечебное дело, педиатрия)"
        result = [
            {'uid': "332",
             'name':
                 {'firstName': u"Наталья",
                  'patronymic': u"Геннадьевна",
                  'lastName': u"Логинова"
                 },
             'hospitalUid': "17/52",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': '50bddafa2a889bb40e000822',
             },
            ]
        doctors = self.client.service.listDoctors({
            'searchScope': {'hospitalUid': hospital_Uid, }, 'speciality': speciality
        })
        self.assertIsInstance(doctors.doctors, list)
        self.assertListEqual(doctors.doctors, result)

    def testListDoctorsKorus20_1(self):
        hospital_Uid = '1111'
        speciality = u"Акушер-гинеколог (лечебное дело, педиатрия)"
        result = []
        doctors = self.client.service.listDoctors({
            'searchScope': {'hospitalUid': hospital_Uid, }, 'speciality': speciality
        })
        if doctors:
            self.assertIsInstance(doctors.doctors, list)
            self.assertListEqual(doctors.doctors, result)

    def testListDoctorsKorus20_2(self):
        hospital_Uid = '1111'
        speciality = "1111"
        result = []
        doctors = self.client.service.listDoctors({
            'searchScope': {'hospitalUid': hospital_Uid, }, 'speciality': speciality
        })
        if doctors:
            self.assertIsInstance(doctors.doctors, list)
            self.assertListEqual(doctors.doctors, result)

    def testListDoctorsKorus20_3(self):
        hospital_Uid = '17/52'
        speciality = "1111"
        result = []
        doctors = self.client.service.listDoctors({
            'searchScope': {'hospitalUid': hospital_Uid, }, 'speciality': speciality
        })
        if doctors:
            self.assertIsInstance(doctors.doctors, list)
            self.assertListEqual(doctors.doctors, result)

    def testListDoctorsKorus20_4(self):
        hospital_Uid = "17/53"
        result = [
            {'uid': "299",
             'name':
                 {'firstName': u"Ольга",
                  'patronymic': u"Александровна",
                  'lastName': u"Бирючкова"
                 },
             'hospitalUid': "17/53",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': 'None',
             },
            {'uid': "323",
             'name':
                 {'firstName': u"Светлана",
                  'patronymic': u"Николаевна",
                  'lastName': u"Мезенцева"
                 },
             'hospitalUid': "17/53",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': 'None',
             },
            {'uid': "323",
             'name':
                 {'firstName': u"Антонина",
                  'patronymic': u"Степановна",
                  'lastName': u"Мякинькова"
                 },
             'hospitalUid': "17/53",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': '50bddb28bb4d33e2830006c4',
             },
            {'uid': "296",
             'name':
                 {'firstName': u"Татьяна",
                  'patronymic': u"Яковлевна",
                  'lastName': u"Полунова"
                 },
             'hospitalUid': "17/53",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': 'None',
             },
            {'uid': "297",
             'name':
                 {'firstName': u"Анна",
                  'patronymic': u"Александровна",
                  'lastName': u"Родикова"
                 },
             'hospitalUid': "17/53",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': '50be00dd2a889bb4090012d1',
             },
            {'uid': "298",
             'name':
                 {'firstName': u"Ольга",
                  'patronymic': u"Вячеславовна",
                  'lastName': u"Тишина"
                 },
             'hospitalUid': "17/53",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': '50bdea212a889bb40e001334',
             },
            {'uid': "322",
             'name':
                 {'firstName': u"Лидия",
                  'patronymic': u"Васильевна",
                  'lastName': u"Ульянова"
                 },
             'hospitalUid': "17/53",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': '50be0110bb4d33e26e0014c2',
             },
        ]
        doctors = self.client.service.listDoctors({'searchScope': {'hospitalUid': hospital_Uid, }})
        self.assertIsInstance(doctors.doctors, list)
        self.assertListEqual(doctors.doctors, result)

    def testListDoctorsKorus20_5(self):
        hospital_Uid = "17/52"
        result = [
            {'uid': "305",
             'name':
                 {'firstName': u"Дмитрий",
                  'patronymic': u"Борисович",
                  'lastName': u"Василистов"
                 },
             'hospitalUid': "17/52",
             'speciality': u"Травматолог-ортопед (лечебное дело, педиатрия)",
             'keyEPGU': '50bdda53ef2455f7d4000330',
             },
            {'uid': "306",
             'name':
                 {'firstName': u"Ольга",
                  'patronymic': u"Викторовна",
                  'lastName': u"Громова"
                 },
             'hospitalUid': "17/52",
             'speciality': u"Травматолог-ортопед (лечебное дело, педиатрия)",
             'keyEPGU': '50bdda7e2a889bb40a0003be',
             },
            {'uid': "290",
             'name':
                 {'firstName': u"Николай",
                  'patronymic': u"Григорьевич",
                  'lastName': u"Клепиков"
                 },
             'hospitalUid': "17/52",
             'speciality': u"Детский хирург (лечебное дело, педиатрия)",
             'keyEPGU': '50bddaa8ef2455f7da0006a3',
             },
            {'uid': "315",
             'name':
                 {'firstName': u"Галина",
                  'patronymic': u"Тимофеевна",
                  'lastName': u"Лесных"
                 },
             'hospitalUid': "17/52",
             'speciality': u"Дерматовенеролог (лечебное дело, педиатрия)",
             'keyEPGU': '50bddad02a889bb40a0003cd',
             },
            {'uid': "332",
             'name':
                 {'firstName': u"Наталья",
                  'patronymic': u"Геннадьевна",
                  'lastName': u"Логинова"
                 },
             'hospitalUid': "17/52",
             'speciality': u"Акушер-гинеколог (лечебное дело, педиатрия)",
             'keyEPGU': '50bddafa2a889bb40e000822',
             },
            ]
        doctors = self.client.service.listDoctors({'searchScope': {'hospitalUid': hospital_Uid, }})
        self.assertIsInstance(doctors.doctors, list)
        self.assertListEqual(doctors.doctors, result)

    def testListDoctorsKorus20_6(self):
        # hospital_Uid = "11111"
        result = []
        doctors = self.client.service.listDoctors()
        if doctors:
            self.assertIsInstance(doctors.doctors, list)
            self.assertListEqual(doctors.doctors, result)

    def testListDoctorsIntramed(self):
        hospital_Uid = "11"
        result = []
        doctors = self.client.service.listDoctors({'searchScope': {'hospitalUid': hospital_Uid, }})
        if doctors:
            self.assertIsInstance(doctors.doctors, list)
#            self.assertListEqual(doctors.doctors, result)


    def testListSpecialities(self):
        specialities = self.client.service.listSpecialities({'hospitalUid': '17/53', 'hospitalUidFrom': '500'})
        self.assertIsInstance(specialities.speciality, list)

    def testListServTypesInfo(self):
        pass


# class TestInfoWSDL(unittest.TestCase):
#     client = Client(IS % "info", cache=None)
#
#     def testGetHospitalInfoKorus20(self):
#         hospitalUid = '17/0'
#         result = [{'uid': "17/0",
#                    'title': u"ГБУЗ «Пензенская областная детская клиническая больница им. Н. Ф. Филатова»",
#                    'type': "None",
#                    'phone': "(8412) 42-75-73",
#                    'email': "odbpost@sura.ru",
#                    'siteURL': "None",
#                    'schedule': "None",
#                    'buildings': [{'title':u"Поликлиника консультативно-диагностическая №1 (для детей)",
#                                   'address': "None",
#                                   'phone': "(8412) 42-75-73",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Поликлиника консультативно-диагностическая №2 (для женщин)",
#                                   'address': "None",
#                                   'phone': "(8412) 42-75-73",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Центр планирования семьи и репродукции",
#                                   'address': "None",
#                                   'phone': "(8412) 42-75-73",
#                                   'schedule': "None",
#                                   },
#                                  ],
#                    },]
#         info_list = self.client.service.getHospitalInfo({'hospitalUid': hospitalUid})
#         self.assertIsInstance(info_list.info, list)
#         self.assertListEqual(info_list.info, result)
#
#     def testGetHospitalInfoIntramed(self):
#         hospitalUid = '11/0'
#         result = [{
#             'siteURL': None,
#             'uid': "11/0",
#             'schedule': None,
#             'phone': None,
#             'type': None,
#             'name': u"ГБУЗ «Кузнецкая ЦРБ»"
#         }]
#         info_list = self.client.service.getHospitalInfo({'hospitalUid': hospitalUid})
#         self.assertIsInstance(info_list.info, list)
#         self.assertListEqual(info_list.info, result)
#
#     def testGetHospitalInfoKorus30(self):
#         hospitalUid = '41/0'
#         result = [{
#             'siteURL': None,
#             'uid': "41/0",
#             'schedule': None,
#             'phone': None,
#             'type': None,
#             'name': u"ФГБУ «ФНКЦ ДГОИ им. Дмитрия Рогачева» Минздрава России"
#         }]
#         info_list = self.client.service.getHospitalInfo({'hospitalUid': hospitalUid})
#         self.assertIsInstance(info_list.info, list)
#         self.assertListEqual(info_list.info, result)
#
#     def testGetHospitalInfo(self):
#         result = [{'uid': "5/0",
#                    'title': u"ГБУЗ «Пензенская областная клиническая больница им. Н.Н. Бурденко»",
#                    'type': "None",
#                    'phone': "8412(32-03-57)",
#                    'email': "burdenko@e-pen.ru",
#                    'siteURL': "None",
#                    'schedule': "None",
#                    'buildings': [{'title':u"Главные специалисты МЗ и СР ПО",
#                                   'address': "None",
#                                   'phone': "8412(32-03-57)",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Диабетологический центр",
#                                   'address': "None",
#                                   'phone': "8412(32-03-57)",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Кабинеты поликлиники",
#                                   'address': "None",
#                                   'phone': "8412(32-03-57)",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Кардиологический диспансер",
#                                   'address': "None",
#                                   'phone': "8412(32-03-57)",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Профпатологический центр",
#                                   'address': "None",
#                                   'phone': "8412(32-03-57)",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Эндоскопическое отделение",
#                                   'address': "None",
#                                   'phone': "8412(32-03-57)",
#                                   'schedule': "None",
#                                   },
#                                  ],
#                    },
#                    {'uid': "17/0",
#                    'title': u"ГБУЗ «Пензенская областная детская клиническая больница им. Н. Ф. Филатова»",
#                    'type': "None",
#                    'phone': "(8412) 42-75-73",
#                    'email': "odbpost@sura.ru",
#                    'siteURL': "None",
#                    'schedule': "None",
#                    'buildings': [{'title':u"Поликлиника консультативно-диагностическая №1 (для детей)",
#                                   'address': "None",
#                                   'phone': "(8412) 42-75-73",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Поликлиника консультативно-диагностическая №2 (для женщин)",
#                                   'address': "None",
#                                   'phone': "(8412) 42-75-73",
#                                   'schedule': "None",
#                                   },
#                                  {'title':u"Центр планирования семьи и репродукции",
#                                   'address': "None",
#                                   'phone': "(8412) 42-75-73",
#                                   'schedule': "None",
#                                   },
#                                  ],
#                    },
#                    {'uid': "11/0",
#                    'title': u"ГБУЗ «Кузнецкая ЦРБ»",
#                    'type': "None",
#                    'phone': "(841-57) 2-05-99",
#                    'email': "kuzn_crb@sura.ru",
#                    'siteURL': "None",
#                    'schedule': "None",
#                    'buildings': [{'title':u'ОБУЗ "ОБЛАСТНОЙ ПЕРИНАТАЛЬНЫЙ ЦЕНТР"',
#                                   'address': "None",
#                                   'phone': "(841-57) 2-05-99",
#                                   'schedule': "None",
#                                   },
#                                  ],
#                    },]
#         info_list = self.client.service.getHospitalInfo()
#         self.assertIsInstance(info_list.info, list)
#         self.assertIn(result, info_list.info)
#
#     def testGetDoctorInfo(self):
#         pass
#
#     def testGetHospitalUidKorus20(self):
#         code = '580064'
#         result = 17
#         id = self.client.service.getHospitalUid({'hospitalCode': code})
#         if id:
#             self.assertEqual(id.hospitalUid, result)
#
#
# class TestScheduleWSDL(unittest.TestCase):
#     client = Client(IS % "schedule", cache=None)
#
#     def testGetScheduleInfoKorus20(self):
# #        hospitalUid = '17/53'
# #        doctorUid = '344'
# #        ticket = self.client.service.getScheduleInfo({'hospitalUid': hospitalUid, 'doctorUid': doctorUid})
# #        self.assertIsInstance(ticket, soap_models.GetScheduleInfoResponse)
# #        self.assertGreater(len(ticket), 0)
#
#         hospitalUid = '19/44'
#         doctorUid = '293'
#         ticket = self.client.service.getScheduleInfo({'hospitalUid': hospitalUid, 'doctorUid': doctorUid})
#         if hasattr(ticket, 'timeslots'):
#             self.assertIsInstance(ticket.timeslots, list)
#             self.assertGreater(ticket.timeslots, 0)
#
#     def testGetScheduleInfoKorus30(self):
#         hospitalUid = '41/3'
#         doctorUid = '242'
#         ticket = self.client.service.getScheduleInfo({'hospitalUid': hospitalUid, 'doctorUid': doctorUid})
#         if ticket:
#             self.assertIsInstance(ticket, list)
#             self.assertIsNotNone(ticket)
#
#     def testGetScheduleInfoIntramed(self):
#         hospitalUid = '11/1025801446528'
#         doctorUid = '19'
#         speciality = u'Акушер-гинеколог'
#         ticket = self.client.service.getScheduleInfo(
#             {'hospitalUid': hospitalUid, 'doctorUid': doctorUid, 'speciality': speciality}
#         )
#         self.assertIsInstance(ticket.timeslots, list)
#         self.assertIsNotNone(ticket.timeslots)
#
#     def testGetTicketStatus(self):
#         hospitalUid = 0
#         ticketUid = 0
#         ticket = self.client.service.getTicketStatus({'hospitalUid':hospitalUid, 'ticketUid': ticketUid})
#         self.assertIsNone(ticket)
#
#     def testSetTicketReadStatus(self):
#         pass
#
#     def testEnqueueKorus20(self):
#         person={'firstName': u"Асия", 'lastName': u"Абаева", 'patronymic': u"Абдуловна", }
#         omiPolicyNumber="4106 5801954102020017"
#         hospitalUid="17/53"
#         doctorUid="344"
#         timeslotStart=(datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d") + "T15:00:00"
#         hospitalUidFrom=0
#         birthday="1954-10-20"
#
#         ticket = self.client.service.enqueue({
#             'person': person,
#             'omiPolicyNumber': omiPolicyNumber,
#             'hospitalUid': hospitalUid,
#             'doctorUid': doctorUid,
#             'timeslotStart': timeslotStart,
#             'hospitalUidFrom': hospitalUidFrom,
#             'birthday': birthday
#         })
#
# #        self.assertIsInstance(ticket, soap_models.EnqueueResponse)
#         if ticket['result'] == 'true':
#             self.assertIn('ticketUid', ticket)
#
#         if ticket['ticketUid'] == "":
#             self.assertNotIn(ticket['result'], ("", "true"))
#
#         # TODO: разобрать варианты с проверкой ограничений по дате рождения и полу
#
#     def testEnqueueKorus30(self):
#         person={'firstName': u"Асия", 'lastName': u"Абаева", 'patronymic': u"Абдуловна", }
#         omiPolicyNumber="4106 5801954102020017"
#         hospitalUid="41/3"
#         doctorUid="242"
#         timeslotStart=(datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d") + "T14:00:00"
#         hospitalUidFrom=12
#         birthday="1954-10-20"
#
#         ticket = self.client.service.enqueue({
#             'person': person,
#             'omiPolicyNumber': omiPolicyNumber,
#             'hospitalUid': hospitalUid,
#             'doctorUid': doctorUid,
#             'timeslotStart': timeslotStart,
#             'hospitalUidFrom': hospitalUidFrom,
#             'birthday': birthday
#         })
#
# #        self.assertIsInstance(ticket, dict)
#         if ticket['result'] == 'true':
#             self.assertIn('ticketUid', ticket)
#
#         if ticket['ticketUid'] == "":
#             self.assertNotIn(ticket['result'], ("", "true"))
#
#         # TODO: разобрать варианты с проверкой ограничений по дате рождения и полу
# #
#     def testEnqueueIntramed(self):
#         person={'firstName': u"Асия", 'lastName': u"Абаева", 'patronymic': u"Абдуловна", }
#         omiPolicyNumber="4106 5801954102020017"
#         hospitalUid="11/1025801446528"
#         doctorUid="19"
#         timeslotStart=(datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d") + "T15:00:00"
#         hospitalUidFrom=0
#         birthday="1954-10-20"
#
#         ticket = self.client.service.enqueue({
#             'person': person,
#             'omiPolicyNumber': omiPolicyNumber,
#             'hospitalUid': hospitalUid,
#             'doctorUid': doctorUid,
#             'timeslotStart': timeslotStart,
#             'hospitalUidFrom': hospitalUidFrom,
#             'birthday': birthday
#         })
#
# #        self.assertIsInstance(ticket, dict)
#         if ticket['result'] == 'true':
#             self.assertIn('ticketUid', ticket)
#
#         if ticket['ticketUid'] == "":
#             self.assertNotIn(ticket['result'], ("", "true"))
#         # TODO: разобрать варианты с проверкой ограничений по дате рождения и полу
#
#     def testCancel(self):
#         pass
#

if __name__ == '__main__':
    unittest.main()