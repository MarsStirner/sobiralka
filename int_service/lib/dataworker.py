# -*- coding: utf-8 -*-

import exceptions
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import or_

from settings import DB_CONNECT_STRING
from models import LPU, LPU_Units, UnitsParentForId, Enqueue, Personal

engine = create_engine(DB_CONNECT_STRING)
Session = sessionmaker(bind=engine)

class DataWorker(object):
    '''
    Provider class for current DataWorkers
    '''

    def __init__(self, type):
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

    def get_list(self, **kwargs):
        if kwargs['lpu_ids']:
            lpu_ids = kwargs['lpu_ids']
        if kwargs['speciality']:
            speciality = kwargs['speciality']
        if kwargs['okato_code']:
            okato_code = kwargs['okato_code']

        # Prepare query for getting LPU
        fields = [LPU.id, LPU.name, LPU.phone, LPU.address, LPU.token, LPU.key]
        filter = []
        join = []

        if speciality and isinstance(speciality, unicode):
            fields.append(Personal.speciality)

        query_lpu = self.session.query(*fields)

        if speciality and isinstance(speciality, unicode):
            query_lpu = query_lpu.join(Personal)
            query_lpu = query_lpu.filter(Personal.speciality==speciality)

        if len(lpu_ids):
            query_lpu = query_lpu.filter(LPU.lpu_ids.in_(lpu))

        if okato_code:
            query_lpu = query_lpu.filter(LPU.OKATO.like('%' + okato_code + '%'))

        return query_lpu.all()

    def get_list_hospitals(self, id, speciality="", ocato_code=""):
        result = {'hospitals':[]}
        lpu = []
        lpu_units = []

        if id:
            if not isinstance(id, list):
                id = list(id)
            for i in id:
                tmp_list = i.split('/')
                if tmp_list[1]:
                    lpu_units.append(tmp_list)
                else:
                    lpu.append(tmp_list[0])

        lpu_list = self.get_list(lpu_ids=lpu, speciality=speciality, okato_code=okato_code)
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
            lpu_units_list = units_dw.get_list(lpu_units_uids=lpu_units, speciality=speciality)
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
                    'wsdlURL': "http://" + SOAP_SERVER_HOST + ":" + SOAP_SERVER_PORT + '/schedule/?wsdl',
                    'token': item.token,
                    'key': item.key,
                    }
                )
        return result


class LPU_UnitsWorker(object):
    session = Session
    model = LPU_Units

    def get_list(self, **kwargs):
        if kwargs['lpu_units_ids']:
            lpu_units_ids = kwargs['lpu_units_ids']
        if kwargs['speciality']:
            speciality = kwargs['speciality']

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
                query_lpu_units = query_lpu_units.filter(or_(LPU_Units.lpuId==unit[0], LPU_Units.id==unit[1]))

        if speciality and isinstance(speciality, unicode):
            query_lpu_units = query_lpu_units.filter(Personal.speciality==speciality)

        return query_lpu_units.all()


class EnqueueWorker(object):
    session = Session
    model = Enqueue
    pass

class PersonalWorker(object):
    session = Session
    model = Personal

    def get_list_doctors(self):
        pass