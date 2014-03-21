# -*- coding: utf-8 -*-
import base64
from suds.client import Client
from suds import WebFault
import settings
import urllib2
import socket
from ..utils import logger

from jinja2 import Environment, PackageLoader

logger_tags = dict(tags=['epgu2_client', 'IS'])


class ClientEPGU():
    """Класс клиента для взаимодействия с ЕПГУ"""

    def __init__(self, source_token):
        self.url = settings.EPGU_SERVICE_URL
        self.client = None
        self.jinja2env = Environment(loader=PackageLoader('int_service', 'templates'))
        self.messageSourceToken = source_token

    def __check_url(self, url):
        try:
            if urllib2.urlopen(url, timeout=2).getcode() == 200:
                return True
        except urllib2.URLError, e:
            print e
            logger.error(e.message, extra=logger_tags)
        except socket.timeout, e:
            print e
            logger.error(e.message, extra=logger_tags)
        return False

    def __init_client(self):
        if not self.client:
            if self.__check_url(self.url):
                if settings.DEBUG:
                    self.client = Client(self.url, cache=None)
                else:
                    self.client = Client(self.url)

    def __send(self, method, message=None):
        self.__init_client()
        params = dict()
        params['messageCode'] = method
        params['messageSourceToken'] = self.messageSourceToken
        if message:
            params['message'] = base64.b64encode(message.encode('utf-8'))
        if self.client:
            return self.client.service.Send(MessageData={'AppData': params})
        else:
            return None

    def __generate_message(self, params):
        template = self.jinja2env.get_template('epgu_message.tpl')
        if isinstance(params, list):
            result = []
            for value in params:
                result.append(self.__generate_message(value))
            return u''.join(result)
        if isinstance(params, dict):
            for k, v in params.items():
                if isinstance(v, (dict, list)) and k != 'params':
                    params[k] = self.__generate_message(v)
        return self.__strip_message(template.render(params=params))

    def __strip_message(self, message):
        return u''.join([string.strip() for string in message.splitlines()])

    def GetMedicalSpecializations(self, auth_token):
        """Получает список специальностей из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)

        <medical-specialization>
            <id>4f882b982bcfa5145a00036c</id>
            <name>Аллергология и иммунология</name>
            <description/>
        </medical-specialization>
        <medical-specialization>
            <id>4f882b982bcfa5145a00036d</id>
            <name>Анестезиология и реаниматология</name>
            <description/>
        </medical-specialization>
        <medical-specialization>
            <id>4f882b982bcfa5145a00036e</id>
            <name>Гастроэнтерология</name>
            <description/>
        </medical-specialization>

        Тег id – идентификатор специальности в справочнике ЕПГУ
        Тег name – название специальности в справочнике ЕПГУ
        """
        try:
            message = self.__generate_message(dict(params={'auth_token': auth_token}))
            result = self.__send('GetSpecs', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            medical_specializations = getattr(result.AppData, 'medical-specializations', None)
            if medical_specializations:
                return medical_specializations
            return getattr(result.AppData, 'errors', None)
        return None

    def GetReservationTypes(self, auth_token):
        """Получает список типов записи из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)

        <reservation-type>
            <id>4f8805b52bcfa52299000011</id>
            <name>Автоматическая запись</name>
            <code>automatic</code>
        </reservation-type>
        <reservation-type>
            <id>4f8805b52bcfa52299000013</id>
            <name>Запись по листу ожидания</name>
            <code>waiting_list</code>
        </reservation-type>
        <reservation-type>
            <id>4f8805b52bcfa52299000012</id>
            <name>Запись с подтверждением</name>
            <code>manual</code>
        </reservation-type>

        Тег id – идентификатор типа записи в справочнике ЕПГУ
        Тег name – название типа записи в справочнике ЕПГУ
        Тег code – код типа записи в справочнике ЕПГУ

        По умолчанию использовать значение automatic.
        """
        try:
            message = self.__generate_message(dict(params={'auth_token': auth_token}))
            result = self.__send('GetReservationTypes', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            reservation_types = getattr(result.AppData, 'reservation-types', None)
            if reservation_types:
                return reservation_types
            return getattr(result.AppData, 'errors', None)
        return None

    def GetPaymentMethods(self, auth_token):
        """Получает список методов оплаты из ЕПГУ

        Args:
            auth_token: указывается token ЛПУ (обязательный)

        <payment-method>
            <id>4f8804ab2bcfa520e6000003</id>
            <name>Бюджетные пациенты</name>
            <default/>
        </payment-method>
        <payment-method>
            <id>4f8804ab2bcfa520e6000002</id>
            <name>Пациенты ДМС</name>
            <default/>
        </payment-method>
        <payment-method>
            <id>4f8804ab2bcfa520e6000001</id>
            <name>Пациенты с полисами ОМС</name>
            <default>true</default>
        </payment-method>


        Тег id – идентификатор метода оплаты в справочнике ЕПГУ
        Тег name – название метода оплаты в справочнике ЕПГУ
        Тег default – используется ли данный метод по умолчанию

        По умолчанию для значения Пациенты с полисами ОМС использовать тег default = true.
        """
        try:
            message = self.__generate_message(dict(params=dict(auth_token=auth_token)))
            result = self.__send('GetPaymentMethods', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            payment_methods = getattr(result.AppData, 'payment-methods', None)
            if payment_methods:
                return payment_methods
            return getattr(result.AppData, 'errors', None)
        return None

    def GetServiceTypes(self, auth_token, ms_id=None):
        """Получает список медицинских услуг из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)
            ms_id: указывается идентификатор медицинской специализации (необязательный)

        <service-type>
            <id>4f993422ef245509c20001d3</id>
            <name>Ангиография артерии верхней конечности прямая</name>
            <recid>828</recid>
            <code>A0612018</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001d4</id>
            <name>Ангиография артерии верхней конечности ретроградная</name>
            <recid>829</recid>
            <code>A0612019</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001c9</id>
            <name>Ангиография артерии щитовидной железы</name>
            <recid>818</recid>
            <code>A0612008</code>
        </service-type>

        Тег id – идентификатор метода оплаты в справочнике ЕПГУ
        Тег name – название метода оплаты в справочнике ЕПГУ

        По умолчанию для значения Пациенты с полисами ОМС использовать тег default = true.
        """
        try:
            params = dict(auth_token=auth_token)
            if ms_id:
                params.update(dict(ms_id=ms_id))
            message = self.__generate_message(dict(params=params))
            result = self.__send('GetServices', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            service_types = getattr(result.AppData, 'service-types', None)
            if service_types:
                return service_types
            return getattr(result.AppData, 'errors', None)
        return None

    def GetServiceType(self, auth_token, service_type_id):
        """Получает вид услуги по идентификатору из ЕПГУ:

        Args:
            auth_token: указывается token ЛПУ (обязательный)
            ms_id: указывается идентификатор медицинской услуги (обязательный)

        <service-type>
            <id>4f993422ef245509c20001d3</id>
            <name>Ангиография артерии верхней конечности прямая</name>
            <recid>828</recid>
            <code>A0612018</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001d4</id>
            <name>Ангиография артерии верхней конечности ретроградная</name>
            <recid>829</recid>
            <code>A0612019</code>
        </service-type>
        <service-type>
            <id>4f993422ef245509c20001c9</id>
            <name>Ангиография артерии щитовидной железы</name>
            <recid>818</recid>
            <code>A0612008</code>
        </service-type>

        Тег id – идентификатор метода оплаты в справочнике ЕПГУ
        Тег name – название метода оплаты в справочнике ЕПГУ

        По умолчанию для значения Пациенты с полисами ОМС использовать тег default = true.
        """
        try:
            message = self.__generate_message(dict(params={'auth_token': auth_token,
                                                           ':service_type_id': service_type_id}))
            result = self.__send('GetService', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            service_type = getattr(result.AppData, 'service-type', None)
            if service_type:
                return service_type
            return getattr(result.AppData, 'errors', None)
        return None

    def GetPlaces(self, **kwargs):
        pass

    def GetPlace(self, auth_token, place_id='current'):
        """Получает код ЛПУ из БД ЕПГУ

        Args:
            auth_token: указывается token ЛПУ (обязательный)
            place_id: всегда указывается current (??) (обязательный)

        Returns:
            Идентификатор ЛПУ. Пример:
            {'id': '4f880ca42bcfa5277202f051',
             'name': u'ГУЗ "ПЕНЗЕНСКАЯ ОБЛАСТНАЯ КЛИНИЧЕСКАЯ БОЛЬНИЦА ИМ.Н.Н.БУРДЕНКО"'
             }

        """
        try:
            message = self.__generate_message(dict(params={':place_id': place_id, 'auth_token': auth_token}))
            result = self.__send('GetMo', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                places = getattr(result.AppData, 'places', None)
                if places:
                    return places
                return getattr(result.AppData, 'errors', None)
        return None

    def GetLocations(self, hospital, service_type_id=None, page=1):
        """Получает список врачей для указанного ЛПУ по указанному типу услуг

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            service_type_id: идентификатор услуги в ЕПГУ, получаемый в GetServiceType (необязательный)
            page: (необязательный) № страницы. По умолчанию 1-я, количество записей на странице - 10 шт

        Returns:
            массив ФИО врачей:
            [{'prefix': u'Ененко У.С. - хирург', }]

        """
        try:
            params = {':place_id': hospital['place_id'],
                      'auth_token': hospital['auth_token'],
                      'page': page}
            if service_type_id:
                params['service_type_id'] = service_type_id,
            message = self.__generate_message(dict(params=params))
            result = self.__send('GetResource', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            place_locations_data = getattr(result.AppData, 'place-locations-data', None)
            if place_locations_data:
                return place_locations_data
            return getattr(result.AppData, 'errors', None)
        return None

    def GetLocation(self):
        pass

    def DeleteEditLocation(self, hospital, location_id):
        """Помечает врача как удаленного на ЕПГУ

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            location_id: (обязательный) идентификатор редактируемой очереди

        """
        try:
            params = dict()
            params['params'] = {'auth_token': hospital['auth_token'],
                                ':place_id': hospital['place_id'],
                                ':location_id': location_id,
                                }
            message = self.__generate_message(params)
            result = self.__send('DeleteResource', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def PostLocations(self, hospital, doctor, service_types, can_write=None):
        """Используется для создания очереди в федеральной регистратуре (на ЕПГУ)

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            doctor: (обязательный) словарь с информацией о враче, вида:
                {'prefix': название очереди (ФИО?),
                 'medical_specialization_id': код специальности (Speciality.nameEPGU),
                 'cabinet_number': ?? номер кабинета (#TODO: дописать ИС для получение кабинета),
                 'time_table_period': количество дней на которое будет доступно расписание
                    (Определяется максимальной датой, на которую доступно расписание для данного врача.
                    Данный параметр можно вынести в файл настроек. По умолчанию значение 90)
                 'reservation_time': время (в минутах) приема врача
                    (необходимо высчитывать время приема для каждого врача индивидуально как разницу между началом и
                    окончанием приема одного пациента на первый день получаемого расписания),
                 'reserved_time_for_slot': время между талонами на прием (?равно времени указанном в reservation_time),
                 'reservation_type_id': идентификатор типа записи, полученный в GetServiceType,
                 'payment_method_id': идентификатор вида оплаты, полученный в GetPaymentMethods,
                }
            service_types: (обязательный) список кодов мед. услуг из GetServiceType, вида:
                ['4f882b9c2bcfa5145a0006e8', ]
            can_write: (необязательный) строка через запятую без пробелов из тех,
                кто имеет доступ к записи в данную очередь. если массив пустой, то записаться никто не сможет.
                если параметр не присылать, то по умолчанию доступ к записи имеют все
                (возможные значения: registry, epgu, call_center, terminal, mis);

        Returns:
            Словарь с информацией о созданной записи, вида:
            {'created-at': '2012-09-12T14:59:04+04:00',
             'id': '50506af8bb4d3371b8028ea3',
             'medical-specialization-id': '4f882b982bcfa5145a000383'
            }

        """
        try:
            params = dict()
            try:
                params['prefix'] = doctor['prefix']
                params['medical_specialization_id'] = doctor['medical_specialization_id']
                params['cabinet_number'] = doctor['cabinet_number']
                params['time_table_period'] = doctor['time_table_period']
                params['reservation_time'] = doctor['reservation_time']
                params['reserved_time_for_slot'] = doctor['reserved_time_for_slot']
                params['reservation_type_id'] = doctor['reservation_type_id']
                params['payment_method_id'] = doctor['payment_method_id']
                params['auto_start'] = 1

                if can_write:
                    params['can_write'] = can_write

                service_type_ids = dict()
                for k, service_type in enumerate(service_types):
                    service_type_ids['st%d' % k] = service_type
                params['service_types_ids'] = service_type_ids

                params['params'] = {':place_id': hospital['place_id'], 'auth_token': hospital['auth_token']}
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(location=params))
                result = self.__send('CreateResource', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            location = getattr(result.AppData, 'location', None)
            if location:
                return location
            return getattr(result.AppData, 'errors', None)
        return None

    def PutEditLocation(self, hospital, doctor, service_types, can_write=None):
        """Используется для редактировани очереди в федеральной регистратуре (на ЕПГУ)

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            doctor: (обязательный) словарь с информацией о враче, вида:
                {'prefix': название очереди (ФИО?),
                 'location_id': идентификатор врача (очереди),
                 'medical_specialization_id': код специальности (Speciality.nameEPGU),
                 'cabinet_number': номер кабинета ,
                 'time_table_period': количество дней на которое будет доступно расписание
                    (Определяется максимальной датой, на которую доступно расписание для данного врача.
                    Данный параметр можно вынести в файл настроек. По умолчанию значение 90)
                 'reservation_time': время (в минутах) приема врача
                    (необходимо высчитывать время приема для каждого врача индивидуально как разницу между началом и
                    окончанием приема одного пациента на первый день получаемого расписания),
                 'reserved_time_for_slot': время между талонами на прием (?равно времени указанном в reservation_time),
                 'reservation_type_id': идентификатор типа записи, полученный в GetServiceType,
                 'payment_method_id': идентификатор вида оплаты, полученный в GetPaymentMethods,
                }
            service_types: (обязательный) список кодов мед. услуг из GetServiceType, вида:
                ['4f882b9c2bcfa5145a0006e8', ]
            can_write: (необязательный) строка через запятую без пробелов из тех,
                кто имеет доступ к записи в данную очередь. если массив пустой, то записаться никто не сможет.
                если параметр не присылать, то по умолчанию доступ к записи имеют все
                (возможные значения: registry, epgu, call_center, terminal, mis);

        Returns:
            Словарь с информацией о созданной записи, вида:
            {'created-at': '2012-09-12T14:59:04+04:00',
             'id': '50506af8bb4d3371b8028ea3',
             'medical-specialization-id': '4f882b982bcfa5145a000383'
            }

        """
        try:
            params = dict()
            try:
                params['prefix'] = doctor['prefix']
                params['medical_specialization_id'] = doctor['medical_specialization_id']
                params['cabinet_number'] = doctor['cabinet_number']
                params['time_table_period'] = doctor['time_table_period']
                params['reservation_time'] = doctor['reservation_time']
                params['reserved_time_for_slot'] = doctor['reserved_time_for_slot']
                params['reservation_type_id'] = doctor['reservation_type_id']
                params['payment_method_id'] = doctor['payment_method_id']
                params['auto_start'] = 1

                service_type_ids = dict()
                for k, service_type in enumerate(service_types):
                    service_type_ids['st%d' % k] = service_type
                params['service_types_ids'] = service_type_ids

                params['params'] = {':place_id': hospital['place_id'],
                                    'auth_token': hospital['auth_token'],
                                    ':location_id': doctor['location_id']}
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(location=params))
                result = self.__send('UpdateResource', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            location = getattr(result.AppData, 'location', None)
            if location:
                return location
            return getattr(result.AppData, 'errors', None)
        return None

    def PostRules(self, hospital, doctor, period, days, can_write=None):
        """Добавляет расписание на ЕПГУ

        Args:
            doctor: (обязательный) строка, ФИО врача,
            period: (обязательный) строка, период, на которые передаётся расписание,
            days: (обязательный) массив, содержащий расписание по датам, вида:
                [{'date': дата,
                  'interval': - массив интервалов, вида:
                      [{'start': время начала приёма,
                      'end': время окончания приёма,},
                      {'start': время начала приёма,
                      'end': время окончания приёма,},
                      ]
                }],
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            can_write: (необязательный) строка через запятую без пробелов из тех,
                кто имеет доступ к записи в данную очередь. если массив пустой, то записаться никто не сможет.
                если параметр не присылать, то по умолчанию доступ к записи имеют все
                (возможные значения: registry, epgu, call_center, terminal, mis);

        Returns:
            Словарь с информацией о созданном расписании, вида:
            {'id': '50507480ef2455c01202a0ca', # идентификатор расписания
             'name': u'Новое расписание', # наименование расписания
            }

        """
        try:
            params = dict()
            try:
                params['schedules_rule'] = dict(name=u'%s (%s)' % (doctor, unicode(period)))

                day_rule = dict()
                for day in days:
                    key = 'day%d' % (day['date'].isoweekday() % 7)
                    day_rule[key] = []
                    for k, interval in enumerate(day['interval']):
                        day_rule[key].append({'int%s' % k: dict(time0=interval['start'], time1=interval['end'])})
                params['day_rule'] = day_rule

                if can_write:
                    params['can_write'] = can_write

                params['params'] = {':place_id': hospital['place_id'], 'auth_token': hospital['auth_token']}
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(rule_data=params))
                result = self.__send('CreateRule', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def PutLocationSchedule(self, hospital, location_id, rules):
        """Связывает сотрудников и расписание

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            location_id: (обязательный) строка, id очереди из PostLocations,
            rules: (обязательный) массив словарей с информацией о расписании, вида:
                [{'id': '50507480ef2455c01202a0ca', # идентификатор расписания из PostRules
                 'start': дата начала действия расписания,
                 'end': дата окончания действия расписания
                },]

        Returns:
            Сообщение об ошибке, либо сообщение об успешной записи


        """
        try:
            params = dict()
            try:
                params['applied_short_day'] = None
                params['applied_nonworking_day'] = None
                params['applied_exception'] = None

                applied_rule = dict()
                for k, v in enumerate(rules):
                    applied_rule['rule%d' % (k + 1)] = dict(rule_id=v['id'],
                                                            start_date=v['start'].strftime('%d.%m.%Y'),
                                                            end_date=v['end'].strftime('%d.%m.%Y'),
                                                            type='all')
                params['applied_rule'] = applied_rule

                params['params'] = {':location_id': location_id, 'auth_token': hospital['auth_token']}
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(applied_schedule=params))
                result = self.__send('PutLocationSchedule', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result is not None:
                errors = getattr(result.AppData, 'errors', None)
                if errors:
                    return errors
                return result.AppData
        return None

    def PutActivateLocation(self, hospital, location_id):
        """Активирует расписание

        Args:
            location_id: (обязательный) строка, id врача из PostLocations,
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }

        Returns:
            Сообщение об ошибке, либо сообщение об успешной записи

        """
        try:
            message = self.__generate_message(dict(params={':location_id': location_id,
                                                           'auth_token': hospital['auth_token']}))
            result = self.__send('ActivateResource', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def PostReserve(self, hospital, doctor_id, service_type_id, date, cito=0):
        """Резервирует время на запись

        Args:
            doctor_id: (обязательный) строка, id врача из PostLocations,
            service_type_id: (обязательный) строка, id типа услуги из GetServiceType,
            date: (обязательный) словарь с информацией о расписании, вида:
                {'date': дата приёма,
                 'start_time': время приёма
                }
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            cito: (необязательный) обозначает, что пациент экстренный и может записаться в любое время.
                Список возможных значений: 0 - не экстренный; 1 - экстренный.  Значение поумолчанию - 0

        Возвращает идентификатор зарезервированного слота

        """
        try:
            params = dict()
            try:
                params['location_id'] = doctor_id
                params['service_type_id'] = service_type_id
                params['date'] = date['date']
                params['start_time'] = date['start_time']

                params['params'] = {'auth_token': hospital['auth_token'], ':cito': cito}
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(client_info=params))
                result = self.__send('CreateSlot', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if hasattr(result, 'AppData'):
                errors = getattr(result.AppData, 'errors', None)
                if errors:
                    return errors
                return result.AppData
        return None

    def PutSlot(self, hospital, patient, slot_id):
        """Запрос на получение из федеральной регистратуры факта записи  на оказание услуги

        Args:
            patient: (обязательный) словарь с информацией о пациенте, вида:
                {'name': (обязательный) имя пациента,
                 'surname': (обязательный) фамилия пациента,
                 'patronymic': (необязательный) отчество пациента,
                 'phone': (обязательный) номер телефона в формате +7(код)номер,
                 'id': (обязательный) уникальный идентификатор пациента,
                },
            slot_id: (обязательный) идентификатор зарезервированного слота, в который производится запись,
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }

        """
        try:
            params = dict()
            try:
                params['name'] = base64.b64encode(patient['name'].encode('utf-8'))
                params['surname'] = base64.b64encode(patient['surname'].encode('utf-8'))
                params['patronymic'] = base64.b64encode(patient['patronymic'].encode('utf-8'))
                params['phone'] = patient['phone']
                params['client_id'] = patient['id']

                params['params'] = {'auth_token': hospital['auth_token'], ':slot_id': slot_id}
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(client_info=params))
                result = self.__send('PutSlot', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None

    def DeleteSlot(self, hospital, slot_id, comment=None):
        """Отмена записи на прием к врачу из ЛПУ на ЕПГУ

        Args:
            hospital: (обязательный) словарь с информацией об ЛПУ, вида:
                {'place_id': идентификатор ЛПУ в ЕПГУ, получаемый в GetPlace,
                 'auth_token': token ЛПУ
                }
            slot_id: (обязательный) идентификатор зарезервированного слота, в который производится запись,
            comment: (необязательный) комментарий удаления слота

        """
        try:
            try:
                params = {'auth_token': hospital['auth_token'], ':slot_id': slot_id}
                if comment:
                    params.update(dict(comment=comment))
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(params=params))
                result = self.__send('DeleteSlot', message)
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            errors = getattr(result.AppData, 'errors', None)
            if errors:
                return errors
            return result.AppData
        return None