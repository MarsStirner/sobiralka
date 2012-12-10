# -*- coding: utf-8 -*-

import exceptions
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy.orm.exc import MultipleResultsFound

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT, DB_CONNECT_STRING
from models import LPU, LPU_Units, UnitsParentForId, Enqueue, Personal
from soap_client import Clients

engine = create_engine(DB_CONNECT_STRING)
Session = sessionmaker(bind=engine)

class DataWorker(object):
    '''
    Provider class for current DataWorkers
    '''
    @classmethod
    def provider(cls, type):
        type = type.lower()

        if type == 'lpu':
            obj = LPUWorker()
        elif type == 'lpu_units':
            obj = LPU_UnitsWorker()
        elif type == 'enqueue':
            obj = EnqueueWorker()
        elif type == 'personal':
            obj = PersonalWorker()
        else:
            obj = None
            raise exceptions.NameError

        return obj


class LPUWorker(object):
    session = Session
    model = LPU

    @classmethod
    def parse_hospital_uid(cls, hospitalUid):
        lpu = []
        lpu_units = []
        if not isinstance(hospitalUid, list):
            hospitalUid = list(hospitalUid)
        for i in hospitalUid:
            tmp_list = i.split('/')
            if tmp_list[1]:
                lpu_units.append(tmp_list)
            else:
                lpu.append(tmp_list[0])

        return (lpu, lpu_units)

    def get_list(self, **kwargs):
        '''
        Get LPU list by parameters
        '''
        if kwargs['id']:
            lpu_ids = kwargs['id']
        if kwargs['speciality']:
            speciality = kwargs['speciality']
        if kwargs['okato_code']:
            okato_code = kwargs['okato_code']

        # Prepare query for getting LPU
#        fields = [LPU.id, LPU.name, LPU.phone, LPU.address, LPU.key, LPU.proxy, LPU.token, LPU.protocol]
        fields = [LPU]
        filter = []
        join = []

        if speciality and isinstance(speciality, unicode):
            fields.append(Personal.speciality)

        query_lpu = self.session.query(*fields)

        if speciality and isinstance(speciality, unicode):
            query_lpu = query_lpu.join(Personal)
            query_lpu = query_lpu.filter(Personal.speciality==speciality)

        if len(lpu_ids):
            query_lpu = query_lpu.filter(LPU.id.in_(lpu_ids))

        if okato_code:
            query_lpu = query_lpu.filter(LPU.OKATO.like('%' + okato_code + '%'))

        return query_lpu.all()

    def get_lpu_by_address(self, **kwargs):
        '''
        Get LPU list by address parameters
        '''
        if (kwargs['parsedAddress']['kladrCode']
            and kwargs['parsedAddress']['block']
            and kwargs['parsedAddress']['flat']
#            and kwargs['parsedAddress']['house']['building']
            and kwargs['parsedAddress']['house']['number']
            ):
            # Prepare search parameters
            streetKLADR = kwargs['parsedAddress']['kladrCode']
            pointKLADR = kwargs['parsedAddress']['kladrCode'][0:5].ljust(15, '0')
        else:
            return []

        result = []

        if kwargs['lpu_list']:
            used_proxy = []
            # Use LPU proxy for searching by Soap
            for lpu in kwargs['lpu_list']:
                proxy = lpu['proxy'].split(';')
                if proxy[0] and proxy[0] not in used_proxy:
                    used_proxy.append(proxy[0])
                    proxy_client = Clients.provider(proxy[0])
                    result.append(proxy_client.findOrgStructureByAddress({
                        'serverId': lpu['key'],
                        'number': kwargs['parsedAddress']['house']['number'],
                        'corpus': kwargs['parsedAddress']['house']['building'],
                        'pointKLADR': pointKLADR,
                        'streetKLADR': streetKLADR,
                        'flat': kwargs['parsedAddress']['house']['flat'],
                    }))

        if result:
            result = self._get_lpu_ids(result)

        return result

    def _get_lpu_ids(self, lpu_list):
        '''
        Get ids and OrgIds by lpu data list
        lpu_list contains info from `findOrgStructureByAddress` remote method
        '''
        for key, item in lpu_list:
            query = (self.session.query(UnitsParentForId.OrgId, LPU.id)
                     .filter(UnitsParentForId.LpuId==LPU.id)
                     .filter(LPU.key==item['serverId'])
                     .filter(UnitsParentForId.ChildId==int(item['orgStructureId'])))
            try:
                lpu_ids = query.one()
            except MultipleResultsFound, e:
                print e
            else:
                lpu_list[key]['id'] = lpu_ids.id
                lpu_list[key]['OrgId'] = lpu_ids.OrgId

        return lpu_list

    def get_list_hospitals(self, hospitalUid, speciality="", okato_code=""):
        '''
        Get list of LPUs and LPU_Units
        '''
        result = {'hospitals':[]}
        lpu = []
        lpu_units = []

        if hospitalUid:
            lpu, lpu_units = LPUWorker.parse_hospital_uid(hospitalUid)

        lpu_list = self.get_list(id=lpu, speciality=speciality, okato_code=okato_code)
        # Append LPUs to result
        for item in lpu_list:
            result['hospitals'].append({
                'uid': item.id + '/0',
                'title': item.name,
                'phone': item.phone,
                'address': item.address,
                'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + SOAP_SERVER_PORT + '/schedule/?wsdl',
                'token': item.token,
                'key': item.key,
                }
            )

        if not okato_code:
            units_dw = LPU_UnitsWorker()
            lpu_units_list = units_dw.get_list(uid=lpu_units, speciality=speciality)
            # Append LPU_Units to result
            for item in lpu_units_list:
                if item.parentId:
                    uid = item.id + '/' + item.parentId
                else:
                    uid = item.id +'/0'

                result['hospitals'].append({
                    'uid': uid,
                    'title': item.name,
                    'phone': item.phone,
                    'address': item.address,
                    # TODO: выяснить используется ли wsdlURL и верно ли указан
                    'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + SOAP_SERVER_PORT + '/schedule/?wsdl',
                    'token': item.token,
                    'key': item.key,
                    }
                )
        return result

    def get_info(self, **kwargs):
        '''
        Get info about LPU/LPUs and its Units
        '''
        lpu, lpu_units = [], []
        result = {}
        if kwargs['hospitalUid']:
            lpu, lpu_units = self.parse_hospital_uid(kwargs['hospitalUid'])

        lpu_units_dw = LPU_UnitsWorker()

        for lpu_item in self.get_list(id=lpu):
            units = []
            for lpu_units_item in lpu_units_dw.get_list(uid=lpu_units, lpu_id=lpu_item.id):
                units.append({
                    'id': lpu_units_item.id,
                    'title': lpu_units_item.name,
                    'address': lpu_units_item.address,
                    'phone': lpu_item.phone,
                    'schedule': lpu_item.schedule,
                })

            result['info'].append({
                'uid': lpu_item.id + '/0',
                'title': lpu_item.name,
                'type': lpu_item.type,
                'phone': lpu_item.phone,
                'email': lpu_item.email,
                'siteURL': '',
                'schedule': lpu_item.schedule,
                'buildings': units,
            })

        return result


class LPU_UnitsWorker(object):
    session = Session
    model = LPU_Units

    def get_list(self, **kwargs):
        '''
        Get LPU_Units list by parameters
        '''
        if kwargs['uid']:
            lpu_units_ids = kwargs['uid']
        if kwargs['speciality']:
            speciality = kwargs['speciality']
        if kwargs['lpu_id']:
            lpu_id = kwargs['lpu_id']

        # Prepare query for getting LPU_Units
        fields = [LPU_Units.id, LPU_Units.lpuId, LPU_Units.name, LPU_Units.address,
                  LPU.phone, LPU.token, LPU.key, UnitsParentForId.lpuId.label('parentId')]
        filter = []
        _join = []
        _outerjoin = [LPU, UnitsParentForId]

        if speciality and isinstance(speciality, unicode):
            fields.append(Personal.speciality)
            _join.append(Personal)

        query_lpu_units = self.session.query(*fields)

        if _join:
            for i in _join:
                query_lpu_units = query_lpu_units.join(i)

        if _outerjoin:
            for i in _outerjoin:
                query_lpu_units = query_lpu_units.outerjoin(i)

        if len(lpu_units_ids):
            for unit in lpu_units_ids:
                or_list.append((LPU_Units.lpuId==unit[0], LPU_Units.id==unit[1]))
            query_lpu_units = query_lpu_units.filter(or_(or_list))

        if speciality and isinstance(speciality, unicode):
            query_lpu_units = query_lpu_units.filter(Personal.speciality==speciality)

        if lpu_id:
            query_lpu_units = query_lpu_units.filter(LPU_Units.lpuId==lpu_id)

        return query_lpu_units.all()


class EnqueueWorker(object):
    session = Session
    model = Enqueue
    pass

class PersonalWorker(object):
    session = Session
    model = Personal

    def get_list(self, **kwargs):
        '''
       Get Doctors list by lpu & lpu_units
       '''
        if kwargs['lpu']:
            lpu = kwargs['lpu']
        if kwargs['lpu_units']:
            lpu_units = kwargs['lpu_units']

        result = {}
        query = self.session.query(
            Personal.FirstName,
            Personal.PatrName,
            Personal.LastName,
            Personal.speciality,
            Personal.id,
            Personal.lpuId,
            Personal.orgId,
            Personal.keyEPGU,
            LPU.name.label('lpu_name'),
            LPU_Units.name.label('lpu_units_name'),
            LPU.address.label('lpu_address'),
            LPU_Units.address.label('lpu_units_address'),
            LPU.phone,
            LPU.key,
        )
        or_list = []
        if lpu:
            for item in lpu:
                or_list.append((Personal.lpuId==item['id'],))
        if lpu_units:
            for item in lpu:
                or_list.append((Personal.lpuId==item['id'], Personal.orgId==item['id']))

        query = query.outerjoin(LPU).outerjoin(LPU_Units)

        for value in query.filter(or_(or_list)).all():
            result['doctors'].append({
                'uid': value.id,
                'name': {
                    'firstName': item.FirstName,
                    'patronymic': item.PatrName,
                    'lastName': item.LastName,
                },
                'hospitalUid': value.lpuId + '/' + value.orgId,
                'speciality': value.speciality,
                'keyEPGU': value.keyEPGU,
            })

            result['hospitals'].append({
                'uid': value.lpuId + '/' + value.orgId,
                'title': (value.lpu_name + " " + value.lpu_units_name).trim(),
                'address': (value.lpu_address + " " + value.lpu_units_address).trim(),
                # TODO: выяснить используется ли wsdlURL и верно ли указан
                'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + SOAP_SERVER_PORT + '/schedule/?wsdl',
                'token': '',
                'key': value.key,
            })

        return result

    def get_list_doctors(self, **kwargs):
        '''
        Get doctors list by parameters
        '''
        if kwargs['searchScope']['hospitalUid']:
            lpu, lpu_units = LPU_Worker.parse_hospital_uid(kwargs['searchScope']['hospitalUid'])

        lpu_dw = LPUWorker()
        lpu_list = lpu_dw.get_list(id=lpu)

        if kwargs['searchScope']['address']:
            # TODO: уточнить используется ли поиск по адресу
            lpu_list = lpu_dw.get_lpu_by_address(kwargs['searchScope']['address'], lpu_list)

        lpu_units_dw = LPU_UnitsWorker()
        lpu_units_list = lpu_units_dw.get_list(uid=lpu_units)

        return self.get_list(lpu=lpu_list, lpu_units=lpu_units_list)
