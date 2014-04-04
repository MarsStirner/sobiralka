# -*- coding: utf-8 -*-
try:
    import json
except ImportError:
    import simplejson as json
from sqlalchemy import or_, and_

from settings import SOAP_SERVER_HOST, SOAP_SERVER_PORT
from admin.models import LPU, LPU_Units, Personal, Speciality
from ..service_clients import Clients

from admin.database import Session, shutdown_session
from .lpu import LPUWorker
from .departments import LPU_UnitsWorker

logger_tags = dict(tags=['dataworker', 'IS'])


class PersonalWorker(object):
    """Класс для работы с информацией по врачам"""
    session = Session()
    # session.autocommit = True
    model = Personal

    def __del__(self):
        self.session.close()

    def get_list(self, **kwargs):
        """Возвращает список врачей по переданным параметрам
        Если переданы параметры, то фильтрует список врачей для указанных ЛПУ и/или подразделений

        Args:
            lpu: массив объектов ЛПУ (soap_models.LPU) (необязательный)
            lpu_units: массив объектов подразделений (soap_models.LPU_Units) (необязательный)

        """
        lpu = kwargs.get('lpu')
        lpu_units = kwargs.get('lpu_units')
        speciality = kwargs.get('speciality')
        lastName = kwargs.get('lastName')
        or_list = []
        if lpu_units:
            for item in lpu_units:
                or_list.append(and_(Personal.lpuId == item.lpuId, Personal.orgId == item.orgId))
        elif lpu:
            for item in lpu:
                or_list.append(and_(Personal.lpuId == item.id,))
#         else:
                #TODO: по-хорошему бы расскоментить, чтоб при пустых параметрах была пустота, но сначала нужно изменить код НТК
# #            raise exceptions.AttributeError
#             return []

        query = self.session.query(
            Personal,
            LPU.name.label('lpu_name'),
            LPU_Units.name.label('lpu_units_name'),
            LPU.address.label('lpu_address'),
            LPU_Units.address.label('lpu_units_address'),
            LPU.phone,
            LPU.key,
        )

        query = query.join(Personal.speciality)
        query = query.outerjoin(LPU)
        query = query.outerjoin(LPU_Units, Personal.orgId == LPU_Units.orgId).filter(Personal.lpuId == LPU_Units.lpuId)

        if speciality:
            query = query.filter(or_(Speciality.name == speciality, Speciality.name.like(u'%{0}%'.format(speciality))))
        if lastName:
            query = query.filter(Personal.LastName == lastName)

        query = query.filter(or_(*or_list))
        order_by = kwargs.get('order')
        if order_by:
            query = query.order_by(order_by)
        else:
            query = query.order_by(Personal.LastName, Personal.FirstName, Personal.PatrName)
        return query.all()

    def get_doctor(self, **kwargs):
        """Возвращает информацию о враче

        Args:
            doctor_id: id врача  (обязательный)
            lpu_unit: uid ЛПУ или подразделения, список вида: ['17, 0'],
                соответствует ['LPU_ID', 'LPU_Unit_ID'] (необязательный)

        """
        lpu_unit = kwargs.get('lpu_unit')
        doctor_id = kwargs.get('doctor_id')

        query = self.session.query(Personal)

        if lpu_unit:
            if int(lpu_unit[1]):
                query = query.filter(Personal.lpuId == int(lpu_unit[0]), Personal.orgId == int(lpu_unit[1]))
            else:
                query = query.filter(Personal.lpuId == int(lpu_unit[0]))
        if doctor_id:
            query = query.filter(Personal.doctor_id == int(doctor_id))

        return query.first()

    def get_list_doctors(self, **kwargs):
        """Формирует и возвращает список врачей для SOAP

        Args:
            {'searchScope':
                {
                'hospitalUid': uid ЛПУ или подразделения, строка вида: '17/0',
                    соответствует 'LPU_ID/LPU_Unit_ID' (необязательный),
                'address': адрес пациента, для выборки ЛПУ (необязательный),
                    {'parsedAddress':
                        {'flat': номер квартиры,
                        'house':{
                            'number': Номер дома
                            'building': Указание на литеру, корпус, строение
                        }
                        'block': Номер квартала (для муниципальных образований,
                            в которых адресация зданий производится с помощью кварталов, а не улиц)
                        'kladrCode': Идентификатор по классификатору КЛАДР
                        }
                    }
                }
            'speciality': специальность врача (необязательный),
            'lastName': фамилия врача (необязательный),
            }

        """
        lpu, lpu_list, lpu_units, lpu_units_list = [], [], [], []
        search_scope = kwargs.get('searchScope')

        if search_scope:
            if hasattr(search_scope, 'hospitalUid'):
                lpu, lpu_units = LPUWorker.parse_hospital_uid(search_scope.hospitalUid)
            lpu_dw = LPUWorker()
            if lpu:
                lpu_list = lpu_dw.get_list(id=lpu)

            if hasattr(search_scope, 'address') and search_scope.address:
                # TODO: уточнить используется ли поиск по адресу
                lpu_list = lpu_dw.get_lpu_by_address(search_scope.address, lpu_list)

        if lpu_units:
            lpu_units_dw = LPU_UnitsWorker()
            lpu_units_list = lpu_units_dw.get_list(uid=lpu_units)

        result = dict()
        result['doctors'] = []
        result['hospitals'] = []

        query_result = self.get_list(
            lpu=lpu_list,
            lpu_units=lpu_units_list,
            speciality=kwargs.get('speciality'),
            lastName=kwargs.get('lastName')
        )

        for value in query_result:
            person = value.Personal
            result['doctors'].append({
                'uid': person.doctor_id,
                'name': {
                    'firstName': person.FirstName,
                    'patronymic': person.PatrName,
                    'lastName': person.LastName,
                },
                'hospitalUid': str(person.lpuId) + '/' + str(person.orgId),
                'speciality': person.speciality[0].name,
                'keyEPGU': person.key_epgu.keyEPGU,
            })

            result['hospitals'].append({
                'uid': str(person.lpuId) + '/' + str(person.orgId),
                'name': (unicode(value.lpu_name) + " " + unicode(value.lpu_units_name)).strip(),
                'address': (unicode(value.lpu_address) + " " + unicode(value.lpu_units_address)).strip(),
                # TODO: выяснить используется ли wsdlURL и верно ли указан
                'wsdlURL': 'http://' + SOAP_SERVER_HOST + ':' + str(SOAP_SERVER_PORT) + '/schedule/?wsdl',
                'token': '',
                'key': value.key,
            })

        shutdown_session()
        return result

    def get_list_specialities(self, **kwargs):
        hospital_uid_from = kwargs.get('hospitalUidFrom')
        hospital_uid = kwargs.get('hospitalUid')

        lpu, lpu_list, lpu_units, lpu_units_list = [], [], [], []

        lpu, lpu_units = LPUWorker.parse_hospital_uid(hospital_uid)
        lpu_dw = LPUWorker()
        if lpu:
            lpu_list = lpu_dw.get_list(id=lpu)

        if lpu_units:
            lpu_units_dw = LPU_UnitsWorker()
            lpu_units_list = lpu_units_dw.get_list(uid=lpu_units)

        query_result = self.get_list(
            lpu=lpu_list,
            lpu_units=lpu_units_list,
            speciality=kwargs.get('speciality'),
            lastName=kwargs.get('lastName'),
            order=Speciality.name
        )
        result = dict()
        result['speciality'] = []
        specialities, lpu_specialities = [], []

        if hospital_uid_from:
            if len(lpu_list):
                proxy_client = Clients.provider(lpu_list[0].protocol, lpu_list[0].proxy.split(';')[0])
            elif len(lpu_units_list):
                proxy_client = Clients.provider(lpu_units_list[0].lpu.protocol,
                                                lpu_units_list[0].lpu.proxy.split(';')[0])
            if proxy_client:
                lpu_specialities = proxy_client.getSpecialities(hospital_uid_from)

        for value in query_result:
            _speciality = value.Personal.speciality[0]
            if _speciality.id not in specialities:
                specialities.append(_speciality.id)
                keyEPGU = None
                if _speciality.epgu_speciality:
                    keyEPGU = _speciality.epgu_speciality.keyEPGU
                speciality = {'speciality': _speciality.name,
                              'ticketsPerMonths': -1,
                              'ticketsAvailable': -1,
                              'nameEPGU': keyEPGU,
                              }

                if lpu_specialities:
                    for speciality_quoted in lpu_specialities:
                        if _speciality.name == speciality_quoted.speciality:
                            nameEPGU = ""
                            if hasattr(speciality, 'nameEPGU'):
                                nameEPGU = speciality_quoted.nameEPGU
                            speciality = {'speciality': speciality_quoted.speciality,
                                          'ticketsPerMonths': int(speciality_quoted.ticketsPerMonths),
                                          'ticketsAvailable': int(speciality_quoted.ticketsAvailable),
                                          'nameEPGU': nameEPGU,
                                          }

                result['speciality'].append(speciality)

        shutdown_session()
        return result