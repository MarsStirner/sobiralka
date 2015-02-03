# -*- coding: utf-8 -*-
import base64
import os
import random
import string
import time
from collections import defaultdict
from suds.client import Client
from suds.bindings import binding
from suds import WebFault
from suds.wsse import *
from ..is_exceptions import EPGUError
import settings
import urllib2
import socket
from uuid import uuid4

from lxml import etree
from ..utils import logger

from jinja2 import Environment, PackageLoader
from suds.sax.element import Element

# import logging
# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger('suds.client').setLevel(logging.DEBUG)
# logging.getLogger('suds.transport').setLevel(logging.DEBUG)
# logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)
# logging.getLogger('suds.wsdl').setLevel(logging.DEBUG)


# class CorrectNamespace(MessagePlugin):
#     def marshalled(self, context):
#         soap_env_parent = context.envelope
#         soap_env_parent.updatePrefix('SOAP-ENV', 'http://www.w3.org/2003/05/soap-envelope')


def generate_messageid():
    fmt = 'xxxxxxxx-xxxxx'
    resp = ''

    for c in fmt:
        if c == '-':
            resp += c
        else:
            resp += string.hexdigits[random.randrange(16)]

    return uuid4()

logger_tags = dict(tags=['epgu2_client', 'IS'])


class ClientEPGU2():
    """Класс клиента для взаимодействия с ЕПГУ ФЭР2"""

    def __init__(self, auth_token):
        self.client = None
        self.jinja2env = Environment(loader=PackageLoader('int_service', 'templates'))
        self.auth_token = auth_token
        self.certificate = self.__get_certificate()
        if self.certificate:
            self.url = '{0}/main.wsdl'.format(settings.EPGU2_SERVICE_URL)
        else:
            self.url = '{0}?wsdl'.format(settings.EPGU2_SERVICE_URL)
        self.client_id = settings.EPGU2_CLIENT_ID
        self.wsans = ('wsa', 'http://www.w3.org/2005/08/addressing')
        self.egiszns = ('egisz', 'http://egisz.rosminzdrav.ru')

    def __get_certificate(self):
        dir_name = 'secure'
        _dir = os.path.realpath(dir_name)
        if not os.path.isdir(_dir):
            _dir = os.path.realpath(os.path.join('..', dir_name))
        for _file in os.listdir(_dir):
            if _file.endswith("epgu.pem"):
                return os.path.join(_dir, _file)
                # return os.path.join(_dir, 'old/test.pem') #- для такого варианта ключ корректно достаётся
        return None

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
            client_params = {}
            if self.certificate:
                from sudssigner.plugin import SignerPlugin, BODY_XPATH, TIMESTAMP_XPATH, etree, lxml_nss, envns, wssens
                # client_params['plugins'] = [SignerPlugin(r"{0}".format(self.certificate), keytype='http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411', digestmethod_algorithm='http://www.w3.org/2001/04/xmldsig-more#gostr3411')]
                client_params['plugins'] = [
                    SignerPlugin(
                        r"{0}".format(self.certificate),
                        items_to_sign=[BODY_XPATH,
                                       TIMESTAMP_XPATH,
                                       etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Header/wsa:ReplyTo',
                                                   namespaces=lxml_nss([envns, self.wsans])),
                                       etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Header/wsa:MessageID',
                                                   namespaces=lxml_nss([envns, self.wsans])),
                                       etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Header/wsa:Action',
                                                   namespaces=lxml_nss([envns, self.wsans])),
                                       etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Header/wsa:To',
                                                   namespaces=lxml_nss([envns, self.wsans])),
                                       etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Header/wsa:RelatesTo',
                                                   namespaces=lxml_nss([envns, self.wsans])),
                                       etree.XPath(
                                           '/SOAP-ENV:Envelope/SOAP-ENV:Header/wsse:Security/wsse:BinarySecurityToken',
                                           namespaces=lxml_nss([envns, wssens])),
                                       etree.XPath('/SOAP-ENV:Envelope/SOAP-ENV:Header/egisz:transportHeader',
                                                   namespaces=lxml_nss([envns, self.egiszns]))],
                        keytype='http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411')]
                # client_params['plugins'] = [SignerPlugin(r"{0}".format(self.certificate), keytype=HrefRsaSha1)]
            try:
                binding.envns = ('SOAP-ENV', 'http://www.w3.org/2003/05/soap-envelope')
                client_params['headers'] = {'Content-Type': 'application/soap+xml'}
                if settings.DEBUG:
                    self.client = Client(self.url, cache=None, prettyxml=True, **client_params)
                else:
                    self.client = Client(self.url, prettyxml=True, **client_params)
            except urllib2.URLError, e:
                logger.error(e.message, extra=logger_tags)
                self.client = None

    def __set_headers(self, action):
        # Create the header
        wsans = self.wsans
        egiszns = self.egiszns
        address = Element('Address', ns=wsans).setText('http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous')
        headers = list()
        headers.append(Element('ReplyTo', ns=wsans).insert(address))
        headers.append(Element('To', ns=wsans).setText(settings.EPGU2_SERVICE_URL))
        headers.append(Element('MessageID', ns=wsans).setText(generate_messageid()))
        headers.append(Element('Action', ns=wsans).setText('SendElectronicRegistry'))

        clientEntityId = Element('clientEntityId', ns=egiszns).setText(self.client_id)
        authInfo = Element('authInfo', ns=egiszns).insert(clientEntityId)
        headers.append(Element('transportHeader', ns=egiszns).insert(authInfo))

        self.client.set_options(soapheaders=headers)

    def set_auth_token(self, auth_token):
        self.auth_token = auth_token

    def __xml_to_dict(self, root):
        if root is not None:
            if len(root) == 0:
                out = {root.tag: root.text}
            elif len(root) == 1 or root[0].tag != root[1].tag:
                out = defaultdict(dict)
                for child in root:
                    out[root.tag].update(self.__xml_to_dict(child))
            else:
                out = defaultdict(list)
                for child in root:
                    out[root.tag].append(self.__xml_to_dict(child))
            return out
        return dict()

    def __parse_result(self, xml_string):
        root = etree.fromstring(xml_string)
        return self.__xml_to_dict(root)

    def __send(self, method, params=None):
        self.__init_client()
        self.__set_headers(action=method)

        send_data = dict()
        send_data['messageCode'] = method
        send_data['messageSourceToken'] = self.auth_token

        if params:
            message = self.__generate_message(params)
            send_data['message'] = base64.b64encode(message.encode('utf-8'))
        if self.client:
            result = None
            for i in range(0, 5):
                try:
                    result = self.client.service.Send(MessageData={'AppData': send_data})
                except urllib2.URLError as e:
                    print e
                    time.sleep(2)
                else:
                    break
            app_data = getattr(result, 'AppData', None)
            status = getattr(result, 'Status', None)
            error = getattr(result, 'Error', None)
            if status == 'ok' and app_data:
                try:
                    xml_result = base64.b64decode(app_data)
                except TypeError, e:
                    logger.error(e, extra=logger_tags)
                    raise e
                else:
                    result = self.__parse_result(xml_result)
                return result
            elif status == 'error' and error:
                logger.error(error.errorMessage, extra=logger_tags)
                raise EPGUError(code=error.errorCode, message=error.errorMessage)
        else:
            return None

    def __generate_message(self, params=None):
        template = self.jinja2env.get_template('epgu2_message.tpl')
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

    def GetSpecs(self):
        """Получает список специальностей из ЕПГУ:

        Returns:
        <specs>
            <spec>
                <id>10</id>
                <code>1</code>
                <name>Лечебное дело. Педиатрия</name>
                <recid>1</recid>
                <parent_recid>0</parent_recid>
            </spec>
        </specs>

        Тег id – идентификатор специальности в справочнике ЕПГУ
        Тег name – название специальности в справочнике ЕПГУ
        """
        try:
            result = self.__send('GetSpecs', {'params': {}})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            return result.get('specs', [])
        return None

    def GetPosts(self):
        """Получает список должностей из ЕПГУ:

        Returns:
        <specs>
            <spec>
                <id>63</id>
                <name>врач-терапевт</name>
                <recid>12365</recid>
            </spec>
        </specs>

        1 id: ID должности
        2 name: наименование должности
        3 recid: идентификатор в справочнике НСИ
        """
        try:
            result = self.__send('GetPosts', {'params': {}})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('posts', [])
        return []

    def GetServicesSpecs(self):
        """Получает список специальностей из ЕПГУ:

        Returns:
        <services_specs>
            <service_spec>
            <service_id>5665</service_id>
            <spec_id>2033</spec_id>
            <service_code>B01.001.001</service_code>
            <spec_code>8</spec_code>
            </service_spec>
        </services_specs>

        1 service_id: ID услуги;
        2 spec_id: ID специальности;
        7 service_code: код услуги;
        8 spec_code: код специальности.
        """
        try:
            result = self.__send('GetServicesSpecs')
        except WebFault, e:
            print e
            logger.error(e, extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            return getattr(result, 'specs', None)
        return None

    def GetPayments(self):
        """Получает список методов оплаты из ЕПГУ

        Returns:
        <payments>
            <payment>
                <code>oms</code>
                <name>Пациенты с полисами ОМС</name>
            </payment>
        </payments>

        code: код метода оплаты
        name: наименование метода оплаты

        """
        try:
            result = self.__send('GetPayments')
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                return result.get('payments', [])
        return None

    def GetServices(self, spec_id):
        """Получает список медицинских услуг из ЕПГУ:

        Args:
            spec_id: указывается идентификатор медицинской специализации (обязательный)

        Returns:
        <services>
            <service>
                <id>123</id>
                <spec_recid>324</spec_recid>
                <code>B0100101</code>
                <name>Адаптометрия</name>
            </service>
        </services>

        id: ID услуги
        spec_recid: идентификатор  медицинской специальности из справочника НСИ
        name: наименование услуги
        code: код услуги

        По умолчанию для значения Пациенты с полисами ОМС использовать тег default = true.
        """
        try:
            params = dict()
            if spec_id:
                params.update(dict(spec_id=spec_id))
            result = self.__send('GetServices', dict(params=params))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                return result.get('services', [])
        return None

    def GetService(self, service_id):
        """Получает вид услуги по идентификатору из ЕПГУ:

        Args:
            service_id: ID услуги (обязательный)

        Returns:
        <service>
            <id>123</id>
            <spec_id>324</spec_id>
            <code>B0100101</code>
            <name>Адаптометрия</name>
        </service>

        1 id: ID услуги
        2 spec_id: ID медицинской специальности
        3 code: код услуги
        4 name: наименование услуги

        """
        try:
            result = self.__send('GetService', {':service_type_id': service_id})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                service_type = getattr(result, 'service-type', None)
                if service_type:
                    return service_type
                return getattr(result, 'errors', None)
        return None

    def GetMos(self, **kwargs):
        """Получает вид услуги по идентификатору из ЕПГУ:

        Args:
        <params>
            <name>Багратионовская</name>
            <code>234121</code>
            <region_code>7700000000000</region_code>
            <city_code>7700000000000</city_code>
            <street_code>7700000000000</street_code>
            <payment_method_id>1</payment_method_id>
            <spec_id>123</spec_id>
            <service_id>123</service_id>
        </params>

        1 name: фрагмент названия МО (необязательный);
        5 code: код МО в ФФОМС (необязательный);
        6 region_code: КЛАДР код региона;
        7 city_code:  КЛАДР код города (необязательный);
        8 street_code:  КЛАДР код улицы (необязательный);
        9 payment_method_id: ID метода оплаты (необязательный);
        10 spec_id: ID специальности (необязательный);
        11 service_id: ID услуги (необязательный).

        Returns:
        <mos>
            <mo>
                <id>123</id>
                <oid>123</oid>
                <parent_id>121</parent_id>
                <is_dept>false</is_dept>
                <code>503021</code>
                <name>Детская городская поликлиника №5</name>
                <short_name>ДГП №5</short_name>
                <address>
                <region_code>7700000000000</region_code>
                <city_code>7700000000000</city_code>
                <street_code>7700000000000</street_code>
                <house>69а</house>
                <building>2</building>
                <corpus>3</corpus>
                <longitude>44.2344</longitude>
                <latitude>23.3454545</latitude>
                <google_url>https://maps.google.com/maps?f=d&source=s_d&saddr=&daddr=DJ522,+%D0%A0%D1%83%D0%BC%D1%8B%D0%BD%D0%B8%D1%8F&hl=ru&geocode=CbJY9UBXNn8hFQ29ogIdTohkASkRhdMaYhdTRzGz1h3ikYvebg&sll=44.2344,23.345454&sspn=0.071091,0.169086&vpsrc=6&t=h&g=44.221953,23.365488&mra=mift&ie=UTF8&z=13&iwloc=ddw1</google_url>
                <yandex_url>http://maps.yandex.ru/?text=%D0%A0%D1%83%D0%BC%D1%8B%D0%BD%D0%B8%D1%8F%2C%20%D0%B6%D1%83%D0%B4%D0%B5%D1%86%20%D0%94%D0%BE%D0%BB%D0%B6%2C%20%D0%92%D1%8B%D1%80%D1%82%D0%BE%D0%BF&sll=23.345454%2C44.2344&ll=23.345454%2C44.234400&spn=0.352249%2C0.132553&z=12&l=map</yandex_url>
                <openstreet_url>http://www.openstreetmap.org/#map=5/44.229/23.665</openstreet_url>
                </address>
                <ogrn>123654789</ogrn>
                <okato>0001200</okato>
                <chief> Иванов Иван Иванович</chief>
                <email/>
                <phone/>
                <fax/>
                <time_zone>8</time_zone>
            </mo>
        </mos>

        1 id: ID МО;
        12 oid: единый уникальный идентификатор медицинской организации (OID) по справочнику 1.2.643.5.1.13.2.1.1.178 (Регистр медицинских организаций Российской Федерации, версия 2);
        13 parent_id: ID вышестоящей МО (необязательный);
        14 is_dept: признак отделения МО (необязательный);
        15 code: код МО в ФФОМС
        16 name: наименование;
        17 short_name: краткое наименование ;
        18 address: адрес МО:
        region_code: КЛАДР код региона;
        city_code:  КЛАДР код города;
        street_code:  КЛАДР код улицы;
        house: номер дома;
        building: строение;
        corpus: корпус;
        longitude: долгота;
        latitude: широта;
        google_url: ссылка на местонахождение МО на картах google (необязательный);
        yandex_url: ссылка на местонахождение МО на картах yandex (необязательный);
        openstreet_url: ссылка на местонахождение МО на картах openstreetmap (необязательный);
        19 ogrn: ОГРН;
        20 okato: ОКАТО;
        21 chief: ФИО руководителя МО;
        22 email: email (необязательный);
        23 phone: телефон (необязательный);
        24 fax: факс (необязательный);
        25 time_zone: часовой пояс РФ
        """
        try:
            result = self.__send('GetMos', kwargs)
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                mos = getattr(result, 'mos', None)
                if mos:
                    return getattr(mos, 'mo', None)
                return getattr(result, 'errors', None)
        return None

    def GetMo(self, id, oid):
        """Получает код ЛПУ из БД ЕПГУ

        Args:
            id: ID МО;
            oid: единый уникальный идентификатор медицинской организации (OID) по справочнику 1.2.643.5.1.13.2.1.1.178 (Регистр медицинских организаций Российской Федерации, версия 2).

        Returns:
            <mo>
                <id>123</id>
                <oid>123</oid>
                <parent_id>121</parent_id>
                <is_dept>false</is_dept>
                <code>503021</code>
                <name>Детская городская поликлиника №5</name>
                <short_name>ДГП №5</short_name>
                <address>
                <region_code>7700000000000</region_code>
                <city_code>7700000000000</city_code>
                <street_code>7700000000000</street_code>
                <house>69а</house>
                <building>2</building>
                <corpus>3</corpus>
                <longitude>44.2344</longitude>
                <latitude>23.3454545</latitude>
                <google_url>https://maps.google.com/maps?f=d&source=s_d&saddr=&daddr=DJ522,+%D0%A0%D1%83%D0%BC%D1%8B%D0%BD%D0%B8%D1%8F&hl=ru&geocode=CbJY9UBXNn8hFQ29ogIdTohkASkRhdMaYhdTRzGz1h3ikYvebg&sll=44.2344,23.345454&sspn=0.071091,0.169086&vpsrc=6&t=h&g=44.221953,23.365488&mra=mift&ie=UTF8&z=13&iwloc=ddw1</google_url>
                <yandex_url>http://maps.yandex.ru/?text=%D0%A0%D1%83%D0%BC%D1%8B%D0%BD%D0%B8%D1%8F%2C%20%D0%B6%D1%83%D0%B4%D0%B5%D1%86%20%D0%94%D0%BE%D0%BB%D0%B6%2C%20%D0%92%D1%8B%D1%80%D1%82%D0%BE%D0%BF&sll=23.345454%2C44.2344&ll=23.345454%2C44.234400&spn=0.352249%2C0.132553&z=12&l=map</yandex_url>
                <openstreet_url>http://www.openstreetmap.org/#map=5/44.229/23.665</openstreet_url>
                </address>
                <ogrn>123654789</ogrn>
                <okato>0001200</okato>
                <chief> Иванов Иван Иванович</chief>
                <email/>
                <phone/>
                <fax/>
                <time_zone>8</time_zone>
            </mo>

            1 id: ID МО;
            2 oid: единый уникальный идентификатор медицинской организации (OID) по справочнику 1.2.643.5.1.13.2.1.1.178 (Регистр медицинских организаций Российской Федерации, версия 2);
            3 parent_id: ID вышестоящей МО (необязательный);
            4 is_dept: признак отделения МО (необязательный);
            5 code: код МО в ФФОМС
            6 name: наименование;
            7 short_name: краткое наименование ;
            8 address: адрес МО:
                region_code: КЛАДР код региона;
                city_code:  КЛАДР код города (необязательный);
                street_code:  КЛАДР код улицы (необязательный);
                house: номер дома (необязательный);
                building: строение (необязательный);
                corpus: корпус (необязательный);
                longitude: долгота (необязательный);
                latitude: широта (необязательный);
                google_url: ссылка на местонахождение МО на картах google (необязательный);
                yandex_url: ссылка на местонахождение МО на картах yandex (необязательный);
                openstreet_url: ссылка на местонахождение МО на картах openstreetmap (необязательный);
            9 ogrn: ОГРН;
            10 okato: ОКАТО;
            11 chief: ФИО руководителя МО;
            12 email: email (необязательный);
            13 phone: телефон (необязательный);
            14 fax: факс (необязательный);
            15 time_zone: часовой пояс РФ.
        """
        try:
            message = self.__generate_message(dict(params={'id': id, 'oid': oid}))
            result = self.__send('GetMo', message)
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                places = getattr(result, 'mo', None)
                if places:
                    return places
                return getattr(result, 'errors', None)
        return None

    def GetResources(self, params):
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
            result = self.__send('GetResources', params)
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                resources = result.get('resources', [])
                if not isinstance(resources, list):
                    resources = [resources]
                return resources
        return None

    def GetLocation(self):
        pass

    def DeleteResource(self, resource_id):
        """Данный профиль используется для удаления очереди в федеральной регистратуре

        Args:
            resource_id: ID очереди

        """
        try:
            result = self.__send('DeleteResource', dict(resource=dict(id=resource_id)))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('status', None)
        return None

    def CreateResource(self, params):
        """Используется для создания очереди в федеральной регистратуре (на ЕПГУ)

        Args:
            <resource>
                <spec_id>123</spec_id>
                <norms>
                    <norm>
                        <service_id>23</service_id>
                        <span>2</span>
                    </norm>
                    <norm>
                        <service_id>25</service_id>
                        <span>1</span>
                    </norm>
                </norms>
                <doctor_id>3</doctor_id>
                <area_id>235</area_id>
                <room>301</room>
                <span>12</span>
                <reserve>30</reserve>
                <payment>oms</payment>
                <is_automatic>false</is_automatic>
                <is_autoactivated>false</is_autoactivated>
                <resource_type>single</resource_type>
                <is_dynamic>false</is_dynamic>
                <is_quoted>false</is_quoted>
                <has_waits>true</has_waits>
                <quantum>15</quantum>
                <source_codes>
                    <source_code>reg</source_code>
                    <source_code>epgu</source_code>
                    <source_code>kc</source_code>
                    <source_code>ter</source_code>
                    <source_code>mis</source_code>
                </source_codes>
            </resource>

            1 spec_id: ID медицинской специализации
            5 norms: нормативы времени оказания услуг:
                service_id: ID услуги;
                span: количество квантов времени (quantum), требуемых на оказание услуги (обязательный для динамических очередей);
            2 doctor_id: ID врача
            3 area_id: ID участка (необязательный)
            4 room: номер кабинета  (необязательный)
            5 span: срок составления расписания
            6 reserve: на сколько минут резервируется слот (до подтверждения)
            7 payment_method_id: ID вида оплаты (пациенты ОМС, ДМС и т.п.)
            8 is_automatic: true/false — признак автоматического подтверждения записи на прием
            9 is_autoactivated: true/false — признак того, что очередь активируется автоматически
            10 resource_type: тип очереди:
                single: обычная
                group: групповая
                home: вызовы на дом
            11 is_dynamic: true/false — признак очереди для динамической записи (может быть true только у обычных очередей)
            12 is_quoted: true/false — признак квотируемости очереди
            13 has_waits: true/false — признак возможности записи в лист ожидания для данной очереди (может быть true только для обычных и групповых очередей)
            14 quantum: продолжительность приема (в минутах)
            15 source_codes: коды допустимых источников записи:
                reg — запись через веб-регистратуру;
                epgu — запись с портала госуслуг;
                kc — запись из колл-центра;
                ter — запись с терминалов;
                mis — запись из МИС.

        Returns:
            <resource>
                <id>12323</id>
                <spec_id>123</spec_id>
                <norms>
                    <norm>
                    <service_id>23</service_id>
                    <span>2</span>
                    </norm>
                    <norm>
                    <service_id>25</service_id>
                    <span>1</span>
                    </norm>
                </norms>
                <doctor_id>3</doctor_id>
                <area_id>235</area_id>
                <room>301</room>
                <span>12</span>
                <reserve>30</reserve>
                <payment>oms</payment>
                <is_automatic>false</is_automatic>
                <is_autoactivated>false</is_autoactivated>
                <resource_type>single</resource_type>
                <is_dynamic>false</is_dynamic>
                <is_quoted>false</is_quoted>
                <has_waits>true</has_waits>
                <quantum>15</quantum>
                    <source_codes>
                    <source_code>reg</source_code>
                    <source_code>epgu</source_code>
                    <source_code>kc</source_code>
                    <source_code>ter</source_code>
                    <source_code>mis</source_code>
                </source_codes>
                <status>inactive</status>
            </resource>

        """
        try:
            result = self.__send('CreateResource', dict(resource=params))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('resource', {})
        return None

    def UpdateResource(self, resource_id, params):
        """Используется для редактировани очереди в федеральной регистратуре (на ЕПГУ)

        Args:
            <resource>
                <id>12323</id>
                <spec_id>123</spec_id>
                <norms>
                    <norm>
                        <service_id>23</service_id>
                        <span>2</span>
                    </norm>
                    <norm>
                        <service_id>25</service_id>
                        <span>1</span>
                    </norm>
                </norms>
                <doctor_id>3</doctor_id>
                <area_id>235</area_id>
                <room>301</room>
                <span>12</span>
                <reserve>30</reserve>
                <payment>oms</payment>
                <is_automatic>false</is_automatic>
                <is_autoactivated>false</is_autoactivated>
                <resource_type>single</resource_type>
                <is_dynamic>false</is_dynamic>
                <is_quoted>false</is_quoted>
                <has_waits>true</has_waits>
                <quantum>15</quantum>
                <source_codes>
                    <source_code>reg</source_code>
                    <source_code>epgu</source_code>
                    <source_code>kc</source_code>
                    <source_code>ter</source_code>
                    <source_code>mis</source_code>
                </source_codes>
                <status>inactive</status>
            </resource>

        1 id: ID созданной очереди
        2 spec_id: ID медицинской специализации
        3 norms: нормативы времени оказания услуг:
            service_id: ID услуги;
            span: количество квантов времени (quantum), требуемых на оказание услуги (обязательный для динамических очередей);
        4 doctor_id: ID врача
        5 area_id: ID участка (необязательный)
        6 room: номер кабинета  (необязательный)
        7 span: срок составления расписания
        8 reserve: на сколько минут резервируется слот (до подтверждения)
        9 payment_method_id: ID вида оплаты (пациенты ОМС, ДМС и т.п.)
        10 is_automatic: true/false — признак автоматического подтверждения записи на прием
        11 is_autoactivated: true/false — признак того, что очередь активируется автоматически
        12 resource_type: тип очереди:
            single: обычная
            group: групповая
            home: вызовы на дом
        13 is_dynamic: true/false — признак очереди для динамической записи (может быть true только у обычных очередей)
        14 has_waits: true/false — признак возможности записи в лист ожидания для данной очереди (может быть true только для обычных и групповых очередей)
        15 quantum: продолжительность приема (в минутах)
        16 source_codes: коды допустимых источников записи:
            reg — запись через веб-регистратуру;
            epgu — запись с портала госуслуг;
            kc — запись из колл-центра;
            ter — запись с терминалов;
            mis — запись из МИС.
        17 status: статус очереди:
            active — активна;
            inactive — неактивна;
            deleted — удалена.

        Returns:
            <resource>
                <id>12323</id>
                <spec_id>123</spec_id>
                <norms>
                    <norm>
                    <service_id>23</service_id>
                    <span>2</span>
                    </norm>
                    <norm>
                    <service_id>25</service_id>
                    <span>1</span>
                    </norm>
                </norms>
                <doctor_id>3</doctor_id>
                <area_id>235</area_id>
                <room>301</room>
                <span>12</span>
                <reserve>30</reserve>
                <payment>oms</payment>
                <is_automatic>false</is_automatic>
                <is_autoactivated>false</is_autoactivated>
                <resource_type>single</resource_type>
                <is_dynamic>false</is_dynamic>
                <is_quoted>false</is_quoted>
                <has_waits>true</has_waits>
                <quantum>15</quantum>
                <source_codes>
                    <source_code>reg</source_code>
                    <source_code>epgu</source_code>
                    <source_code>kc</source_code>
                    <source_code>ter</source_code>
                    <source_code>mis</source_code>
                </source_codes>
                <status>inactive</status>
            </resource>

            1 id: ID созданной очереди
            18 spec_id: ID медицинской специализации
            19 norms: нормативы времени оказания услуг:
                service_id: ID услуги;
                span: количество квантов времени (quantum), требуемых на оказание услуги (обязательный для динамических очередей);
            20 doctor_id: ID врача
            21 area_id: ID участка (необязательный)
            22 room: номер кабинета  (необязательный)
            23 span: срок составления расписания
            24 reserve: на сколько минут резервируется слот (до подтверждения)
            25 payment_method_id: ID вида оплаты (пациенты ОМС, ДМС и т.п.)
            26 is_automatic: true/false — признак автоматического подтверждения записи на прием
            27 is_autoactivated: true/false — признак того, что очередь активируется автоматически
            28 resource_type: тип очереди:
                single: обычная
                group: групповая
                home: вызовы на дом
            29 is_dynamic: true/false — признак очереди для динамической записи (может быть true только у обычных очередей)
            30 has_waits: true/false — признак возможности записи в лист ожидания для данной очереди (может быть true только для обычных и групповых очередей)
            31 quantum: продолжительность приема (в минутах)
            32 source_codes: коды допустимых источников записи:
                reg — запись через веб-регистратуру;
                epgu — запись с портала госуслуг;
                kc — запись из колл-центра;
                ter — запись с терминалов;
                mis — запись из МИС.
            33 status: статус очереди:
                active — активна;
                inactive — неактивна;
                deleted — удалена.

        """
        try:
            params.update(dict(id=resource_id))
            result = self.__send('UpdateResource', dict(resource=params))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('resource', {})
        return None

    def CreateRule(self, params):
        """Данный профиль используется для добавления расписания

        Args:
            <rule>
                <resource_id>123</resource_id>
                <name>Расписание 1</name>
                <from>2013-10-20</from>
                <till>2013-11-02</till>
                <consider>all</consider>
                <is_exception>false</is_exception>
                <atoms>
                    <atom>
                        <weekday>1</weekday>
                        <even>true</even>
                        <odd>true</odd>
                        <from>10:00</from>
                        <till>16:00</till>
                        <source_codes>
                            <source_code>reg</source_code>
                            <source_code>epgu</source_code>
                            <source_code>kc</source_code>
                            <source_code>ter</source_code>
                            <source_code>mis</source_code>
                        </source_codes>
                    </atom>
                    <atom>
                        <weekday>2</weekday>
                        <even>true</even>
                        <odd>true</odd>
                        <from>16:00</from>
                        <till>22:00</till>
                        <source_codes>
                            <source_code>reg</source_code>
                            <source_code>epgu</source_code>
                            <source_code>kc</source_code>
                            <source_code>ter</source_code>
                            <source_code>mis</source_code>
                        </source_codes>
                    </atom>
                </atoms>
            </rule>

            1 resource_id: ID очереди
            2 name: название расписания
            3 from: начальная дата действия правила
            4 till: конечная дата действия правила
            5 consider: принимает одно из трех значений:
                all — не учитывать четность/нечетность дней/недель, при этом во всех <atom> параметры even и odd должны быть установлены в true;
                weeks — параметры even и odd в <atom> указывают на четные/нечетные недели и в каждом <atom> должно быть либо even = true и add = false, либо even = false и odd = true;
                days — параметры even и odd в <atom> указывают на четные/нечетные числа мсяца и в каждом <atom> должно быть либо even = true и add = false, либо even = false и odd = true;
            6 is_exception: принимает одно из двух значений:
                true — это правило является исключением и имеет приоритет над обычными правилами, действующими в указанный период дат;
                false — это обычное правило;
            7 atoms: список элементарных периодов времени <atom> с указанием источников записи:
                weekday: номер дня недели (0 — понедельник, 6 — воскресенье);
                even: true/false — признак того, что действие периода распространяется на четные числа или четные недели (см. consider);
                odd: true/false — признак того, что действие периода распространяется на нечетные числа или нечетные недели (см. consider);
                from: время начала действие периода;
                till: время окончания действия периода;
                source_codes: коды допустимых источников записи:
                    reg — запись через веб-регистратуру;
                    epgu — запись с портала госуслуг;
                    kc — запись из колл-центра;
                    ter — запись с терминалов;
                    mis — запись из МИС.

        Returns:
            <rule>
                <id>5432</id>
                <resource_id>123</resource_id>
                <name>Расписание 1</name>
                <from>2013-10-20</from>
                <till>2013-11-02</till>
                <consider>all</consider>
                <is_exception>false</is_exception>
                <atoms>
                    <atom>
                        <weekday>1</weekday>
                        <even>true</even>
                        <odd>true</odd>
                        <from>10:00</from>
                        <till>16:00</till>
                        <source_codes>
                            <source_code>reg</source_code>
                            <source_code>epgu</source_code>
                            <source_code>kc</source_code>
                            <source_code>ter</source_code>
                            <source_code>mis</source_code>
                        </source_codes>
                    </atom>
                    <atom>
                        <weekday>2</weekday>
                        <even>true</even>
                        <odd>true</odd>
                        <from>16:00</from>
                        <till>22:00</till>
                        <source_codes>
                            <source_code>reg</source_code>
                            <source_code>epgu</source_code>
                            <source_code>kc</source_code>
                            <source_code>ter</source_code>
                            <source_code>mis</source_code>
                        </source_codes>
                    </atom>
                </atoms>
            </rule>

            Параметры ответа:
            1 id: ID расписания
            8 resource_id: ID очереди
            9 name: название расписания
            10 from: начальная дата действия правила
            11 till: конечная дата действия правила
            12 consider: принимает одно из трех значений:
                all — не учитывать четность/нечетность дней/недель, при этом во всех <atom> параметры even и odd должны быть установлены в true;
                weeks — параметры even и odd в <atom> указывают на четные/нечетные недели и в каждом <atom> должно быть либо even = true и add = false, либо even = false и odd = true;
                days — параметры even и odd в <atom> указывают на четные/нечетные числа мсяца и в каждом <atom> должно быть либо even = true и add = false, либо even = false и odd = true;
            2 is_exception: принимает одно из двух значений:
                true — это правило является исключением и имеет приоритет над обычными правилами, действующими в указанный период дат;
                false — это обычное правило;
            3 atoms: список элементарных периодов времени <atom> с указанием источников записи:
                weekday: номер дня недели (0 — понедельник, 6 — воскресенье);
                even: true/false — признак того, что действие периода распространяется на четные числа или четные недели (см. consider);
                odd: true/false — признак того, что действие периода распространяется на нечетные числа или нечетные недели (см. consider);
                from: время начала действие периода;
                till: время окончания действия периода;
                source_codes: коды допустимых источников записи:
                    reg — запись через веб-регистратуру;
                    epgu — запись с портала госуслуг;
                    kc — запись из колл-центра;
                    ter — запись с терминалов;
                    mis — запись из МИС.

        """
        try:
            result = self.__send('CreateRule', params)
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('rule', {})
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

                params['params'] = {':location_id': location_id}
            except AttributeError, e:
                print e
                logger.error(e, extra=logger_tags)
                return None
            else:
                message = self.__generate_message(dict(applied_schedule=params))
                result = self.__send('PutLocationSchedule', message)
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                errors = getattr(result, 'errors', None)
                if errors:
                    return errors
                return result
        return None

    def ActivateResource(self, resource_id):
        """Активирует очередь

        Args:
            resource_id: (обязательный) ID очереди

        Returns:
            Сообщение об ошибке, либо сообщение об успешной записи

        """
        try:
            result = self.__send('ActivateResource', dict(resource={'id': resource_id}))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('status', None)
        return None

    def DeactivateResource(self, resource_id):
        """Активирует очередь

        Args:
            resource_id: (обязательный) ID очереди

        Returns:
            Сообщение об ошибке, либо сообщение об успешной записи

        """
        try:
            result = self.__send('DeactivateResource', dict(resource={'id': resource_id}))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('status', None)
        return None

    def CreateDoctor(self, params):
        """Данный профиль используется для заведения нового специалиста в МО

        Args:
            <doctor>
                <snils>12345678901</snils>
                <surname>Никитина</surname>
                <name>Татьяна</name>
                <patronymic>Николаевна</patronymic>
                <spec_ids>
                    <spec_id>1</spec_id>
                    <spec_id>2</spec_id>
                </spec_ids>
                <post_ids>
                    <post_id>1</post_id>
                    <post_id>2</post_id>
                <post_id>3</post_id>
                </post_ids>
            </doctor>

            1 surname: фамилия специалиста
            127 name: имя специалиста
            128 patronymic: отчество специалиста (необязательный)
            129 snils: СНИЛС специалиста
            130 spec_ids: ID специальностей
            131 posts_ids: ID должностей

        Returns:
            <doctor>
                <id>23</id>
                <snils>12345678901</snils>
                <surname>Никитина</surname>
                <name>Татьяна</name>
                <patronymic>Николаевна</patronymic>
                <spec_ids>
                    <spec_id>1</spec_id>
                    <spec_id>2</spec_id>
                </spec_ids>
                <post_ids>
                    <post_id>1</post_id>
                    <post_id>2</post_id>
                <post_id>3</post_id>
                </post_ids>
            </doctor>

            1 id: ID созданного специалиста
            132 surname: фамилия специалиста
            133 name: имя специалиста
            134 patronymic: отчество специалиста
            135 snils: СНИЛС специалиста
            136 spec_ids: ID специальностей
            137 posts_ids: ID должностей

        """
        try:
            result = self.__send('CreateDoctor', dict(doctor=params))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('doctor', None)
        return None

    def UpdateDoctor(self, doctor_id, params):
        """Данный профиль используется для изменения параметров специалиста в МО

        Args:
            <doctor>
                <id>123</id>
                <snils>12345678901</snils>
                <surname>Никитина</surname>
                <name>Татьяна</name>
                <patronymic>Николаевна</patronymic>
                <spec_ids>
                    <spec_id>1</spec_id>
                </spec_ids>
                <post_ids>
                    <post_id>1</post_id>
                    <post_id>2</post_id>
                </post_ids>
            </doctor>

            1 id: ID специалиста
            2 surname: фамилия специалиста
            138 name: имя специалиста
            139 patronymic: отчество специалиста (необязательный)
            140 snils: СНИЛС специалиста
            141 spec_ids: ID специальностей
            142 posts_ids: ID должностей


        Returns:
            <doctor>
                <id>23</id>
                <snils>12345678901</snils>
                <surname>Никитина</surname>
                <name>Татьяна</name>
                <patronymic>Николаевна</patronymic>
                <spec_ids>
                    <spec_id>1</spec_id>
                    <spec_id>2</spec_id>
                </spec_ids>
                <post_ids>
                    <post_id>1</post_id>
                    <post_id>2</post_id>
                <post_id>3</post_id>
                </post_ids>
            </doctor>

            1 id: ID специалиста
            143 surname: фамилия специалиста
            144 name: имя специалиста
            145 patronymic: отчество специалиста
            146 snils: СНИЛС специалиста
            147 spec_ids: ID специальностей
            148 posts_ids: ID должностей

        """
        try:
            params.update(dict(id=doctor_id))
            result = self.__send('UpdateDoctor', dict(doctor=params))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('doctor', None)
        return None

    def DeleteDoctor(self, doctor_id):
        """Данный профиль используется для удаления специалиста в МО

        Args:
            <doctor>
                <id>123</id>
            </doctor>

            doctor_id ID специалиста

        Returns:
            <doctor>
               <status>ok</status>
            </doctor>

            1 status: статус удаления информации о специалисте

        """
        try:
            result = self.__send('DeleteDoctor', dict(doctor={'id': doctor_id}))
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                return result.get('doctor', None)
        return None

    def GetDoctors(self, mo_id=None, spec_id=None):
        """Данный профиль используется для получения перечня специалистов МО

        Args:
            <params>
                <mo_id>123</mo_id>
                <spec_id>1</spec_id>
            </params>

            1 mo_id: ID МО (необязательный)
            149 spec_id: ID специальности (необязательный)

        Returns:
            <doctors>
                <doctor>
                    <id>23</id>
                    <snils>12345678901</snils>
                    <surname>Никитина</surname>
                    <name>Татьяна</name>
                    <patronymic>Николаевна</patronymic>
                    <spec_ids>
                        <spec_id>1</spec_id>
                        <spec_id>2</spec_id>
                    </spec_ids>
                    <post_ids>
                        <post_id>1</post_id>
                        <post_id>2</post_id>
                        <post_id>3</post_id>
                    </post_ids>
                </doctor>
            </doctors>

            1 id: ID специалиста
            150 surname: фамилия специалиста
            151 name: имя специалиста
            152 patronymic: отчество специалиста
            153 snils: СНИЛС специалиста
            154 spec_ids: ID специальностей
            155 posts_ids: ID должностей

        """
        try:
            params = dict()
            result = self.__send('GetDoctors', {'params': params})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                doctors = result.get('doctors', [])
                if not isinstance(doctors, list):
                    doctors = [doctors]
                return doctors
        return None

    def CreateSlot(self, resource_id, service_id, slot_datetime):
        """Резервирует время на запись

        Args:
            <slot>
                <resource_id>123</resource_id>
                <service_id>243</service_id>
                <date>2013-10-29</date>
                <from>10:00</from>
                <is_urgent>false</is_urgent>
            </slot>

            1 resource_id: ID очереди;
            2 service_id: ID вида услуги;
            3 date: дата приема;
            4 from: время начала приема;
            5 is_urgent: признак экстренного приема (необязательный).

        Returns:
            <slot>
                <id>123</id>
                <mo_id>543</mo_id>
                <resource_id>123</resource_id>
                <patient/>
                <service_id>243</service_id>
                <date>2013-10-29</date>
                <from>10:00</from>
                <till>10:15</till>
                <is_urgent>false</is_urgent>
                <status>reserved</status>
                <source_code>mis</source_code>
                <reject_reason/>
                <number>42</number>
                <source_mis_id>4535</source_mis_id>
                <source_mo_id>876</source_mo_id>
                <quota_number/>
                <additions/>
            </slot>

            1 id: ID записи на прием;
            6 mo_id: ID МО;
            7 resource_id: ID очереди;
            8 patient: информация о пациенте (необязательный);
            9 service_id: ID вида услуги;
            10 date: дата приема;
            11 from: время начала приема в минутах с 00:00;
            12 till: время окончания приема в минутах с 00:00;
            13 is_urgent: признак экстренного вызова (необязательный);
            14 status: статус записи на прием;
            15 source_code: код источника записи;
            16 reject_reason: причина отказа в записи на прием;
            17 number: порядковый номер записи на прием, уникален в рамках даты приёма и медицинской организации;
            18 source_mis_id: ID записавшей МИС;
            19 source_mo_id: ID записавшей МО;
            20 quota_number: квота;
            21 additions: дополнительная информация для вызовов на дом.

        """
        params = dict()
        params['resource_id'] = resource_id
        params['service_id'] = service_id
        params['date'] = slot_datetime.strftime('%Y-%m-%d')
        params['from'] = slot_datetime.strftime('%H:%M')

        try:
            result = self.__send('CreateSlot', {'slot': params})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('slot', {})
        return None

    def FinishCreateSlot(self, slot_id, patient):
        """Запрос на получение из федеральной регистратуры факта записи на оказание услуги

        Args:
            <slot>
                <id>123</id>
                <patient>
                    <snils/>
                    <passport/>
                    <oms>1234567890123456</oms>
                    <is_parental>false</is_parental>
                    <surname>Иванов</surname>
                    <name>Иван</name>
                    <patronymic>Иваныч</patronymic>
                    <gender>male</gender>
                    <birthday>1990-01-01</birthday>
                    <email>foo@bar.com</email>
                    <phone>+7 (123) 456-78-90</phone>
                </patient>
            </slot>

            1 id: ID записи на прием
            22 patient: сведения о пациенте:
                surname: фамилия;
                name: имя;
                patronymic: отчество;
                birthday: дата рождения;
                gender: пол;
                snils: СНИЛС, только цифры (необязательный)
                passport: номер паспорта, только цифры (необязательный)
                oms: номер полиса ОМС, только цифры (необязательный)
                is_parental: true/false — признак того, что указан номер полиса ОМС родителя или опекуна (необязательный)
                email: адрес электронной почты (необязательный)
                phone: номер телефона (необязательный)
   
            Примечание:
                Должен присутствовать хотя бы один из параметров snils, passport, oms.

        Returns:
            <slot>
                <id>123</id>
                <mo_id>543</mo_id>
                <resource_id>123</resource_id>
                <patient>
                    <snils>11111111111</snils>
                    <passport>1234567890</passport>
                    <oms>1234567890123456</oms>
                    <is_parental>false</is_parental>
                    <surname>Иванов</surname>
                    <name>Иван</name>
                    <patronymic>Иваныч</patronymic>
                    <gender>male</gender>
                    <birthday>1990-01-01</birthday>
                    <email>foo@bar.com</email>
                    <phone>+7 (123) 456-78-90</phone>
                </patient>
                <service_id>243</service_id>
                <date>2013-10-29</date>
                <from>10:00</from>
                <till>10:15</till>
                <is_urgent>false</is_urgent>
                <status>pending</status>
                <source_code>mis</source_code>
                <reject_reason/>
                <number>42</number>
                <source_mis_id>4535</source_mis_id>
                <source_mo_id>876</source_mo_id>
                <quota_number/>
                <additions/>
            </slot>

            1 id: ID записи на прием
            23 mo_id: ID МО
            24 resource_id: ID очереди
            25 patient: сведения о пациенте:
                surname: фамилия;
                name: имя;
                patronymic: отчество;
                birthday: дата рождения;
                gender: пол;
                snils: СНИЛС, только цифры (необязательный)
                passport: номер паспорта, только цифры (необязательный)
                oms: номер полиса ОМС, только цифры (необязательный)
                is_parental: true/false — признак того, что указан номер полиса ОМС родителя или опекуна (необязательный)
                email: адрес электронной почты (необязательный)
                phone: номер телефона (необязательный)
            2 service_id: ID вида услуги
            3 date: дата приема
            4 from: время начала приема в минутах с 00:00
            5 till: время окончания приема в минутах с 00:00
            6 is_urgent: признак экстренного вызова (необязательный)
            7 status: статус записи на прием
            8 source_code: код источника записи
            9 reject_reason: причина отказа в записи на прием
            10 number: порядковый номер записи на прием, уникален в рамках даты приёма и медицинской организации
            11 source_mis_id: ID записавшей МИС
            12 source_mo_id: ID записавшей МО
            13 quota_number: квота
            14 additions: дополнительная информация для вызовов на дом

        """
        try:
            params = {'slot': {'id': slot_id, 'patient': patient}}
            result = self.__send('FinishCreateSlot', params)
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        else:
            if result:
                return result.get('slot', {})
        return None

    def DeleteSlot(self, slot_id):
        """Отмена записи на прием к врачу из ЛПУ на ЕПГУ

        Args:
            <slot>
                <id>1</id>
            </slot>

        Returns:
            <slot>
                <id>123</id>
                <mo_id>543</mo_id>
                <resource_id>123</resource_id>
                <service_id>243</service_id>
                <date>2013-10-29</date>
                <from>10:00</from>
                <till>10:15</till>
                <is_urgent>false</is_urgent>
                <status>service_is_refused</status>
                <source_code>mis</source_code>
                <reject_reason/>
                <number>42</number>
                <source_mis_id>4535</source_mis_id>
                <source_mo_id>876</source_mo_id>
                <quota_number/>
                <additions/>
            </slot>

            1 id: ID записи на прием
            2 mo_id: ID МО
            3 resource_id: ID очереди
            2 service_id: ID вида услуги
            3 date: дата приема
            4 from: время начала приема в минутах с 00:00
            5 till: время окончания приема в минутах с 00:00
            6 is_urgent: признак экстренного вызова (необязательный)
            7 status: статус записи на прием
            8 source_code: код источника записи
            9 reject_reason: причина отказа в записи на прием
            10 number: порядковый номер записи на прием, уникален в рамках даты приёма и медицинской организации
            11 source_mis_id: ID записавшей МИС
            12 source_mo_id: ID записавшей МО
            13 quota_number: квота
            14 additions: дополнительная информация для вызовов на дом

        """
        try:
            result = self.__send('DeleteSlot', {'slot': {'id': slot_id}})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                return result.get('slot', {})
        return None

    def DeclineSlot(self, slot_id):
        """Данный профиль используется для отклонения заявки на прием

        Args:
            <slot>
                <id>1</id>
            </slot>

        Returns:
            <slot>
                <id>123</id>
                <mo_id>543</mo_id>
                <resource_id>123</resource_id>
                <patient>
                    <snils>11111111111</snils>
                    <passport>1234567890</passport>
                    <oms>1234567890123456</oms>
                    <is_parental>false</is_parental>
                    <surname>Иванов</surname>
                    <name>Иван</name>
                    <patronymic>Иваныч</patronymic>
                    <gender>male</gender>
                    <birthday>1990-01-01</birthday>
                    <email>foo@bar.com</email>
                    <phone>+7 (123) 456-78-90</phone>
                </patient>
                <service_id>243</service_id>
                <date>2013-10-29</date>
                <from>10:00</from>
                <till>10:15</till>
                <is_urgent>false</is_urgent>
                <status>declined</status>
                <source_code>mis</source_code>
                <reject_reason/>
                <number>42</number>
                <source_mis_id>4535</source_mis_id>
                <source_mo_id>876</source_mo_id>
                <quota_number/>
                <additions/>
            </slot>

            1 id: ID записи на прием
            42 mo_id: ID МО
            43 resource_id: ID очереди
            44 patient: сведения о пациенте:
                surname: фамилия;
                name: имя;
                patronymic: отчество;
                gender: пол;
                birthday: дата рождения;
                snils: СНИЛС, только цифры (необязательный)
                passport: номер паспорта, только цифры (необязательный)
                oms: номер полиса ОМС, только цифры (необязательный)
                is_parental: true/false — признак того, что указан номер полиса ОМС родителя или опекуна (необязательный)
                email: адрес электронной почты (необязательный)
                phone: номер телефона (необязательный)
            45 service_id: ID вида услуги
            46 date: дата приема
            47 from: время начала приема в минутах с 00:00
            48 till: время окончания приема в минутах с 00:00
            49 is_urgent: признак экстренного вызова (необязательный)
            50 status: статус записи на прием
            51 source_code: код источника записи
            52 reject_reason: причина отказа в записи на прием
            53 number: порядковый номер записи на прием, уникален в рамках даты приёма и медицинской организации
            54 source_mis_id: ID записавшей МИС
            55 source_mo_id: ID записавшей МО
            56 quota_number: квота
            57 additions: дополнительная информация для вызовов на дом

        """
        try:
            result = self.__send('DeclineSlot', {'slot': {'id': slot_id}})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                return result.get('slot', {})
        return None

    def RefuseSlot(self, slot_id, reject_reason='patient_decline'):
        """Данный профиль используется для освобождения времени записи на прием в связи с отказом от записи

        Args:
            <slot>
                <id>1</id>
                <reject_reason>Другая причина</reject_reason>
            </slot>

            1 id: ID записи на прием
            58 reject_reason: причина отказа
            Для указания причин отказа рекомендуется использовать следующие значения, указанные в формате код:наименование :
                  error_in_slot: Ошибка заполнения заявки;
                  patient_decline: Отказ пациента от записи на прием;
                  incorrect_service: Некорректный выбор услуги;
                  incorrect_data: Предоставление некорректных данных;
                  mo_decline: Отмена записи на прием со стороны МО;
                  no_free_space: Нет свободных мест;
                  no_hospitalization_condition: Нет показаний к госпитализации;
                  no_accept_diagnosis: Не подтвержден диагноз;
                  patient_decline_hospitalization: Пациент отказался от госпитализации;
                  other_reasons: Другие причины.

        Returns:
            <slot>
                <id>123</id>
                <mo_id>543</mo_id>
                <resource_id>123</resource_id>
                <patient>
                    <snils>11111111111</snils>
                    <passport>1234567890</passport>
                    <oms>1234567890123456</oms>
                    <is_parental>false</is_parental>
                    <surname>Иванов</surname>
                    <name>Иван</name>
                    <patronymic>Иваныч</patronymic>
                    <gender>male</gender>
                    <birthday>1990-01-01</birthday>
                    <email>foo@bar.com</email>
                    <phone>+7 (123) 456-78-90</phone>
                </patient>
                <service_id>243</service_id>
                <date>2013-10-29</date>
                <from>10:00</from>
                <till>10:15</till>
                <is_urgent>false</is_urgent>
                <status>service_is_not_provided</status>
                <source_code>mis</source_code>
                <reject_reason>Другая причина</reject_reason>
                <number>42</number>
                <source_mis_id>4535</source_mis_id>
                <source_mo_id>876</source_mo_id>
                <quota_number/>
                <additions/>
            </slot>

            1 id: ID записи на прием
            59 mo_id: ID МО
            60 resource_id: ID очереди
            61 patient: сведения о пациенте:
                surname: фамилия;
                name: имя;
                patronymic: отчество;
                birthday: дата рождения;
                gender: пол;
                snils: СНИЛС, только цифры (необязательный)
                passport: номер паспорта, только цифры (необязательный)
                oms: номер полиса ОМС, только цифры (необязательный)
                is_parental: true/false — признак того, что указан номер полиса ОМС родителя или опекуна (необязательный)
                email: адрес электронной почты (необязательный)
                phone: номер телефона (необязательный)
            2 service_id: ID вида услуги
            3 date: дата приема
            4 from: время начала приема в минутах с 00:00
            5 till: время окончания приема в минутах с 00:00
            6 is_urgent: признак экстренного вызова (необязательный)
            7 status: статус записи на прием
            8 source_code: код источника записи
            9 reject_reason: причина отказа в записи на прием
            10 number: порядковый номер записи на прием, уникален в рамках даты приёма и медицинской организации
            11 source_mis_id: ID записавшей МИС
            12 source_mo_id: ID записавшей МО
            13 quota_number: квота
            14 additions: дополнительная информация для вызовов на дом

        """
        try:
            result = self.__send('RefuseSlot', {'slot': {'id': slot_id, 'reject_reason': reject_reason}})
        except WebFault, e:
            print unicode(e)
            logger.error(unicode(e), extra=logger_tags)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            if result:
                return result.get('slot', {})
        return None