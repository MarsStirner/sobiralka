# -*- coding: utf-8 -*-
import exceptions
import urllib2

try:
    import json
except ImportError:
    import simplejson as json

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm.scoping import ScopedSession

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT, DEBUG
from admin.models import LPU, UnitsParentForId, Speciality, LPU_Specialities
from ..service_clients import Clients
from ..is_exceptions import IS_ConnectionError

from admin.database import Session, shutdown_session
from ..utils import logger
from ..dataworker import DataWorker

logger_tags = dict(tags=['dataworker', 'IS'])


class LPUWorker(object):
    """Класс для работы с информацией по ЛПУ"""
    # session.autocommit = True
    model = LPU

    def __init__(self, session=None):
        if session is not None and isinstance(session, ScopedSession):
            self.session = session
        else:
            self.session = Session()

    def __del__(self):
        self.session.close()

    @classmethod
    def parse_hospital_uid(cls, hospitalUid):
        """Парсит uid ЛПУ, извлекая id ЛПУ и id подразделения

        Args:
            hospitalUid: строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID'

        """
        lpu = []
        lpu_units = []
        if not isinstance(hospitalUid, list):
            hospitalUid = [hospitalUid, ]
        for i in hospitalUid:
            tmp_list = i.split('/')
            if len(tmp_list) > 1 and int(tmp_list[1]):
                lpu.append(int(tmp_list[0]))
                lpu_units.append([int(tmp_list[0]), int(tmp_list[1])])
            else:
                lpu.append(int(tmp_list[0]))
        return lpu, lpu_units

    def get_list(self, **kwargs):
        """Возвращает список ЛПУ

        Args:
            id: массив id ЛПУ для фильтрации (необязательный)
            speciality: врачебная специальность для фильтрации ЛПУ (необязательный)
            okato_code: код ОКАТО для фильтрации ЛПУ (необязательный)

        """
        lpu_ids = kwargs.get('id')
        speciality = kwargs.get('speciality')
        okato_code = kwargs.get('okato_code')

        # Prepare query for getting LPU
#        fields = [LPU.id, LPU.name, LPU.phone, LPU.address, LPU.key, LPU.proxy, LPU.token, LPU.protocol]
        fields = [LPU]
        filter = []
        join = []

        query_lpu = self.session.query(*fields)

        if speciality and isinstance(speciality, unicode):
            query_lpu = query_lpu.join(LPU_Specialities).join(Speciality)
            query_lpu = query_lpu.filter(Speciality.name == speciality)

        if lpu_ids and len(lpu_ids):
            query_lpu = query_lpu.filter(LPU.id.in_(lpu_ids))

        if okato_code:
            query_lpu = query_lpu.filter(LPU.OKATO.like('%' + okato_code + '%'))

        query_lpu = query_lpu.order_by(LPU.name)

        return query_lpu.all()

    def get_lpu_by_address(self, **kwargs):
        """Возвращает список ЛПУ для указанного адреса пациента

        Args:
            parsedAddress: словарь вида,
                {'kladrCode': КЛАДР код населенного пункта,
                 'flat': номер квартиры,
                 'house': {
                    'number': номер дома,
                    'building': литера, корпус, строение, (необязательный)
                 },
                }

        """
        try:
            if (kwargs['parsedAddress']['kladrCode']
                #and kwargs['parsedAddress']['block']
                and kwargs['parsedAddress']['flat']
                #and kwargs['parsedAddress']['house']['building']
                and kwargs['parsedAddress']['house']['number']):
                    # Prepare search parameters
                    streetKLADR = kwargs.get('parsedAddress', {}).get('kladrCode')
                    pointKLADR = kwargs.get('parsedAddress').get('kladrCode')[0:5].ljust(15, '0')
        except exceptions.AttributeError:
            return []

        result = []

        lpu_list = kwargs.get('lpu_list')
        if lpu_list:
            used_proxy = []
            # Use LPU proxy for searching by SOAP
            for lpu in lpu_list:
                proxy = lpu.proxy.split(';')
                if proxy[0] and proxy[0] not in used_proxy:
                    used_proxy.append(proxy[0])
                    proxy_client = Clients.provider(lpu.protocol, proxy[0])
                    result.append(proxy_client.findOrgStructureByAddress({
                        'serverId': lpu.key,
                        'number': kwargs.get('parsedAddress').get('house').get('number'),
                        'corpus': kwargs.get('parsedAddress').get('house', {}).get('building'),
                        'pointKLADR': pointKLADR,
                        'streetKLADR': streetKLADR,
                        'flat': kwargs.get('parsedAddress').get('flat'),
                    }))

        if result:
            result = self._get_lpu_ids(result)

        return result

    def _get_lpu_ids(self, lpu_list):
        """
        Get ids and OrgIds by lpu data list
        lpu_list contains info from `findOrgStructureByAddress` remote method
        """
        for key, item in lpu_list:
            query = (self.session.query(UnitsParentForId.OrgId, LPU.id)
                     .filter(UnitsParentForId.LpuId == LPU.id)
                     .filter(LPU.key == item['serverId'])
                     .filter(UnitsParentForId.ChildId == int(item['orgStructureId'])))
            try:
                lpu_ids = query.one()
            except MultipleResultsFound, e:
                logger.error(e, extra=logger_tags)
                print e
            else:
                lpu_list[key]['id'] = lpu_ids.id
                lpu_list[key]['OrgId'] = lpu_ids.OrgId

        return lpu_list

    def get_list_hospitals(self, **kwargs):
        """Формирует и возвращает список ЛПУ и подразделений для SOAP

        Args:
            hospitalUid: строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный)
            speciality: врачебная специальность для фильтрации ЛПУ (необязательный)
            ocatoCode: код ОКАТО для фильтрации ЛПУ (необязательный)

        """
        result = dict()
        result['hospitals'] = []
        lpu = []
        lpu_units = []

        hospital_uid = kwargs.get('hospitalUid')

        if hospital_uid:
            lpu, lpu_units = LPUWorker.parse_hospital_uid(hospital_uid)

        speciality = kwargs.get('speciality')
        okato_code = kwargs.get('ocatoCode')

        lpu_list = self.get_list(id=lpu, speciality=speciality, okato_code=okato_code)
        # Append LPUs to result
        for item in lpu_list:
            result['hospitals'].append({
                'uid': str(item.id) + '/0',
                'name': item.name,
                'phone': item.phone,
                'address': item.address,
                'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + str(SOAP_SERVER_PORT) + '/schedule/?wsdl',
                'token': item.token,
                'key': item.key,
            })

        if not okato_code:
            units_dw = DataWorker.provider('lpu_units')
            lpu_units_list = units_dw.get_list(uid=lpu_units, speciality=speciality)
            # Append LPU_Units to result
            for item in lpu_units_list:
                uid = str(item.lpuId) + '/' + str(item.orgId)
                if item.parent:
                    uid += '/' + str(item.parent.OrgId)
                else:
                    uid += '/0'

                result['hospitals'].append({
                    'id': item.orgId,
                    'uid': uid,
                    'name': item.name,
                    'phone': item.lpu.phone if item.lpu else '',
                    'address': item.address,
                    # TODO: выяснить используется ли wsdlURL и верно ли указан
                    'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + str(SOAP_SERVER_PORT) + '/schedule/?wsdl',
                    'token': item.lpu.token if item.lpu else '',
                    'key': item.lpu.key if item.lpu else '',
                })
        shutdown_session()
        return result

    def get_info(self, **kwargs):
        """Возвращает список ЛПУ и подразделений по переданным параметрам

        Args:
            hospitalUid: строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный)

        """
        lpu, lpu_units = [], []
        result = []

        hospital_uid = kwargs.get('hospitalUid')
        if hospital_uid:
            lpu, lpu_units = self.parse_hospital_uid(hospital_uid)

        lpu_units_dw = DataWorker.provider('lpu_units')

        for lpu_item in self.get_list(id=lpu):
            units = []
            for lpu_units_item in lpu_units_dw.get_list(uid=lpu_units, lpu_id=lpu_item.id):
                uid = str(lpu_units_item.lpuId) + '/' + str(lpu_units_item.orgId)
                if lpu_units_item.parent:
                    try:
                        uid += '/' + str(getattr(lpu_units_item.parent[0], 'OrgId', 0))
                    except IndexError:
                        uid += '/0'
                else:
                    uid += '/0'

                units.append({
                    'id': lpu_units_item.orgId,
                    'uid': uid,
                    'name': lpu_units_item.name,
                    'address': lpu_units_item.address,
                    'phone': lpu_item.phone,
                    'schedule': lpu_item.schedule,
                })

            result.append({
                'uid': str(lpu_item.id) + '/0',
                'name': lpu_item.name,
                'type': lpu_item.type,
                'phone': lpu_item.phone,
                'email': lpu_item.email if lpu_item.email else '',
                'siteURL': '',
                'schedule': lpu_item.schedule,
                'buildings': units,
            })
        shutdown_session()
        return {'info': result}

    def get_by_id(self, id):
        """
        Get LPU by id and check if proxy url is available
        """
        try:
            result = self.session.query(LPU).filter(LPU.id == int(id)).one()
        except NoResultFound, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            result.proxy = result.proxy.split(';')[0]
            if result.protocol in ('intramed', 'samson', 'korus20'):
                # Проверка для soap-сервисов на доступность, неактуально для thrift (т.е. для korus30)
                try:
                    if not self.__check_proxy(result.proxy):
                        return None
                except IS_ConnectionError, e:
                    logger.error(e, extra=logger_tags)
                    print e
                    return None
            return result
        return None

    def __check_proxy(self, proxy):
        try:
            if urllib2.urlopen(proxy).getcode() == 200:
                return True
        except urllib2.URLError:
            raise IS_ConnectionError(host=proxy)
        return False

    def get_uid_by_code(self, code):
        """
        Get LPU.uid by code
        """
        try:
            result = self.session.query(LPU.id).filter(LPU.key == code).one()
        except NoResultFound, e:
            logger.error(e, extra=logger_tags)
            print e
        except MultipleResultsFound, e:
            logger.error(e, extra=logger_tags)
            print e
        else:
            return result
        return None
