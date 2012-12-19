# -*- coding: utf-8 -*-
import os
import datetime
import int_service.main
import unittest
import logging
from suds.client import Client

logging.basicConfig()

IS = "http://127.0.0.1:9910/%s/?wsdl"

class TestListWSDL(unittest.TestCase):
    client = Client(IS % "list", cache=None)

    def testListHospitals(self):
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
        hospitals = self.client.service.listHospitals(ocatoCode=okato).hospitals
        self.assertIsInstance(hospitals, list)
        self.assertListEqual(hospitals, result)

        okato = "56405000000"
        result = [ {'uid': "11/0",
                    'title': u"ГБУЗ «Кузнецкая ЦРБ»",
                    'phone': "(841-57) 2-05-99",
                    'address': u"Пензенская обл., г. Кузнецк, ул. Сызранская, 142",
                    'wsdlURL': IS + "schedule",
                    'token': "None",
                    'key': "580033"
                   },]
        hospitals = self.client.service.listHospitals(ocatoCode=okato).hospitals
        self.assertIsInstance(hospitals, list)
        self.assertListEqual(hospitals, result)

        okato = "56203000000"
        result = []
        hospitals = self.client.service.listHospitals(ocatoCode=okato).hospitals
        self.assertIsInstance(hospitals, list)
        self.assertListEqual(hospitals, result)

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
        hospitals = self.client.service.listHospitals().hospitals
        self.assertIsInstance(hospitals, list)
        self.assertListEqual(hospitals, result)

        okato = "11111111"
        result = []
        hospitals = self.client.service.listHospitals(ocatoCode=okato).hospitals
        self.assertIsInstance(hospitals, list)
        self.assertListEqual(hospitals, result)

    def testListDoctors(self):
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
        doctors = self.client.service.listDoctors(
            searchScope = {'hospitalUid': hospital_Uid, }, speciality = speciality
        ).doctors
        self.assertIsInstance(doctors, list)

        hospital_Uid = '1111'
        speciality = u"Акушер-гинеколог (лечебное дело, педиатрия)"
        result = []
        doctors = self.client.service.listDoctors(
            searchScope = {'hospitalUid': hospital_Uid, }, speciality = speciality
        ).doctors
        self.assertIsInstance(doctors, list)

        hospital_Uid = '1111'
        speciality = "1111"
        result = []
        doctors = self.client.service.listDoctors(
            searchScope = {'hospitalUid': hospital_Uid, }, speciality = speciality
        ).doctors
        self.assertIsInstance(doctors, list)

        hospital_Uid = '17/52'
        speciality = "1111"
        result = []
        doctors = self.client.service.listDoctors(
            searchScope = {'hospitalUid': hospital_Uid, }, speciality = speciality
        ).doctors
        self.assertIsInstance(doctors, list)

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
        doctors = self.client.service.listDoctors(searchScope = {'hospitalUid': hospital_Uid, }).doctors
        self.assertIsInstance(doctors, list)
        self.assertListEqual(doctors, result)

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
        doctors = self.client.service.listDoctors(searchScope = {'hospitalUid': hospital_Uid, }).doctors
        self.assertIsInstance(doctors, list)
        self.assertListEqual(doctors, result)

        hospital_Uid = "11111"
        result = []
        doctors = self.client.service.listDoctors().doctors
        self.assertIsInstance(doctors, list)
        self.assertListEqual(doctors, result)

    def testListSpecialities(self):
        pass

    def testListServTypesInfo(self):
        pass


class TestInfoWSDL(unittest.TestCase):
    client = Client(IS % "info", cache=None)

    def testGetHospitalInfo(self):
        hospitalUid = '17/0'
        result = [{'uid': "17/0",
                   'title': u"ГБУЗ «Пензенская областная детская клиническая больница им. Н. Ф. Филатова»",
                   'type': "None",
                   'phone': "(8412) 42-75-73",
                   'email': "odbpost@sura.ru",
                   'siteURL': "None",
                   'schedule': "None",
                   'buildings': [{'title':u"Поликлиника консультативно-диагностическая №1 (для детей)",
                                  'address': "None",
                                  'phone': "(8412) 42-75-73",
                                  'schedule': "None",
                                  },
                                 {'title':u"Поликлиника консультативно-диагностическая №2 (для женщин)",
                                  'address': "None",
                                  'phone': "(8412) 42-75-73",
                                  'schedule': "None",
                                  },
                                 {'title':u"Центр планирования семьи и репродукции",
                                  'address': "None",
                                  'phone': "(8412) 42-75-73",
                                  'schedule': "None",
                                  },
                                 ],
                   },]
        info_list = self.client.service.getHospitalInfo({'hospitalUid':hospitalUid})
        self.assertIsInstance(info_list, list)
        self.assertListEqual(info_list, result)

        hospitalUid = '123'
        result = []
        info_list = self.client.service.getHospitalInfo(hospitalUid=hospitalUid)
        self.assertIsInstance(info_list, list)
        self.assertListEqual(info_list, result)

        result = [{'uid': "5/0",
                   'title': u"ГБУЗ «Пензенская областная клиническая больница им. Н.Н. Бурденко»",
                   'type': "None",
                   'phone': "8412(32-03-57)",
                   'email': "burdenko@e-pen.ru",
                   'siteURL': "None",
                   'schedule': "None",
                   'buildings': [{'title':u"Главные специалисты МЗ и СР ПО",
                                  'address': "None",
                                  'phone': "8412(32-03-57)",
                                  'schedule': "None",
                                  },
                                 {'title':u"Диабетологический центр",
                                  'address': "None",
                                  'phone': "8412(32-03-57)",
                                  'schedule': "None",
                                  },
                                 {'title':u"Кабинеты поликлиники",
                                  'address': "None",
                                  'phone': "8412(32-03-57)",
                                  'schedule': "None",
                                  },
                                 {'title':u"Кардиологический диспансер",
                                  'address': "None",
                                  'phone': "8412(32-03-57)",
                                  'schedule': "None",
                                  },
                                 {'title':u"Профпатологический центр",
                                  'address': "None",
                                  'phone': "8412(32-03-57)",
                                  'schedule': "None",
                                  },
                                 {'title':u"Эндоскопическое отделение",
                                  'address': "None",
                                  'phone': "8412(32-03-57)",
                                  'schedule': "None",
                                  },
                                 ],
                   },
                   {'uid': "17/0",
                   'title': u"ГБУЗ «Пензенская областная детская клиническая больница им. Н. Ф. Филатова»",
                   'type': "None",
                   'phone': "(8412) 42-75-73",
                   'email': "odbpost@sura.ru",
                   'siteURL': "None",
                   'schedule': "None",
                   'buildings': [{'title':u"Поликлиника консультативно-диагностическая №1 (для детей)",
                                  'address': "None",
                                  'phone': "(8412) 42-75-73",
                                  'schedule': "None",
                                  },
                                 {'title':u"Поликлиника консультативно-диагностическая №2 (для женщин)",
                                  'address': "None",
                                  'phone': "(8412) 42-75-73",
                                  'schedule': "None",
                                  },
                                 {'title':u"Центр планирования семьи и репродукции",
                                  'address': "None",
                                  'phone': "(8412) 42-75-73",
                                  'schedule': "None",
                                  },
                                 ],
                   },
                   {'uid': "11/0",
                   'title': u"ГБУЗ «Кузнецкая ЦРБ»",
                   'type': "None",
                   'phone': "(841-57) 2-05-99",
                   'email': "kuzn_crb@sura.ru",
                   'siteURL': "None",
                   'schedule': "None",
                   'buildings': [{'title':u'ОБУЗ "ОБЛАСТНОЙ ПЕРИНАТАЛЬНЫЙ ЦЕНТР"',
                                  'address': "None",
                                  'phone': "(841-57) 2-05-99",
                                  'schedule': "None",
                                  },
                                 ],
                   },]
#        info_list = self.client.service.getHospitalInfo()
#        self.assertIsInstance(info_list, list)
#        self.assertListEqual(info_list, result)

    def testGetDoctorInfo(self):
        pass

    def testGetHospitalUid(self):
        pass


class TestScheduleWSDL(unittest.TestCase):
    client = Client(IS % "schedule", cache=None)

    def testGetScheduleInfo(self):
        hospitalUid = '17/53'
        doctorUid = '344'
        ticket = self.client.service.getScheduleInfo(hospitalUid=hospitalUid, doctorUid=doctorUid)
        self.assertIsInstance(ticket, list)
        self.assertGreater(len(ticket), 0)

        ticket = self.client.service.getScheduleInfo()
        self.assertIsInstance(ticket, list)

    def testGetTicketStatus(self):
        hospitalUid = 0
        ticketUid = 0
        ticket = self.client.service.getTicketStatus(hospitalUid=hospitalUid, ticketUid=ticketUid)[0]
        self.assertIsInstance(ticket, list)

    def testSetTicketReadStatus(self):
        pass

    def testEnqueue(self):
        person={'firstName': u"Асия", 'lastName': u"Абаева", 'patronymic': u"Абдуловна", }
        omiPolicyNumber="4106 5801954102020017"
        hospitalUid="17/53"
        doctorUid="344"
        timeslotStart=(datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d") + "T15:00:00"
        hospitalUidFrom=0
        birthday="1954-10-20"

        ticket = self.client.service.enqueue(person=person,
            omiPolicyNumber=omiPolicyNumber,
            hospitalUid=hospitalUid,
            doctorUid=doctorUid,
            timeslotStart=timeslotStart,
            hospitalUidFrom=hospitalUidFrom,
            birthday=birthday)

        self.assertIsInstance(ticket, dict)
        if ticket['result'] == 'true':
            self.assertIn('ticketUid', ticket)

        if ticket['ticketUid'] == "":
            self.assertNotIn(ticket['result'], ("", "true"))

        # TODO: разобрать варианты с проверкой ограничений по дате рождения и полу


    def testCancel(self):
        pass


if __name__ == '__main__':
    unittest.main()