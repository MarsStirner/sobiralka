# -*- coding: utf-8 -*-
import exceptions
import urllib2
import datetime
import time

try:
    import json
except ImportError:
    import simplejson as json
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.scoping import ScopedSession
from suds import WebFault

from admin.models import LPU, LPU_Units, UnitsParentForId, Enqueue, Personal, Speciality, Regions, LPU_Specialities
from admin.models import Personal_Specialities, Personal_KeyEPGU, Post, Personal_Posts
from ..service_clients import Clients
from ..is_exceptions import exception_by_code, IS_ConnectionError

from admin.database import Session, shutdown_session
from ..utils import logger
from ..dataworker import DataWorker


logger_tags = dict(tags=['dataworker', 'IS'])


class UpdateWorker(object):
    """Класс для импорта данных в ИС из КС"""

    def __init__(self, session=None):
        self.msg = []

        if session is not None and isinstance(session, ScopedSession):
            self.session = session
        else:
            self.session = Session()

    def __del__(self):
        self.session.close()

    def __log(self, msg):
        if msg:
            self.msg.append(msg)

    def __init_database(self):
        """Create tables from models if not exists"""
        from admin.database import init_db
        init_db()

    def __get_proxy_address(self, proxy, protocol):
        proxy = proxy.split(';')
        if protocol == 'korus30':
            # не делаем проверку для Thrift, т.к. urllib2.urlopen(proxy) для него не работает
            return proxy[0]
        else:
            if self.__check_proxy(proxy[0]):
                return proxy[0]

    def __check_proxy(self, proxy):
        try:
            if urllib2.urlopen(proxy).getcode() == 200:
                return True
        except urllib2.URLError:
            raise IS_ConnectionError(host=proxy)
        return False

    def __clear_data(self, lpu):
        """Удаляет данные, по указанным ЛПУ"""

        self.session.query(UnitsParentForId).filter(UnitsParentForId.LpuId == lpu.id).delete()

        if lpu.lpu_units:
            [self.session.delete(lpu_unit) for lpu_unit in lpu.lpu_units]

        self.session.query(LPU_Specialities).filter(LPU_Specialities.lpu_id == lpu.id).delete()

        self.session.query(Personal).filter(Personal.lpuId == lpu.id).delete()

        self.session.commit()

    def __check_unit_exists(self, lpu_id, unit_id):
        return self.session.query(LPU_Units).filter(LPU_Units.lpuId == lpu_id, LPU_Units.orgId == unit_id).count()

    def __update_unit_parents(self, units, lpu):
        for unit in units:
            if not unit.name:
                continue
            try:
                if hasattr(unit, 'parentId') and unit.parentId:
                    if self.__check_unit_exists(lpu.id, unit.parentId) > 0:
                        self.session.add(UnitsParentForId(LpuId=lpu.id, OrgId=unit.parentId, ChildId=unit.id))
                        self.session.commit()
                elif hasattr(unit, 'parent_id') and unit.parent_id:
                    if self.__check_unit_exists(lpu.id, unit.parent_id) > 0:
                        self.session.add(UnitsParentForId(LpuId=lpu.id, OrgId=unit.parent_id, ChildId=unit.id))
                        self.session.commit()
            except Exception, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__log(u'Ошибка при добавлении в UnitsParentForId: %s' % e)
                self.session.rollback()

    def __update_lpu_units(self, lpu):
        """Обновляет информацию о потразделениях"""
        return_units = []
        proxy = self.__get_proxy_address(lpu.proxy, lpu.protocol)
        if proxy:
            proxy_client = Clients.provider(lpu.protocol, proxy)
            # В Samson КС предполагается, что сначала выбираются ЛПУ Верхнего уровня и они идут в табл lpu_units,
            # а их дети идут в UnitsParentForId
            # Необходимо с этим разобраться
            # т.е. первая выборка должна быть без parent_id (т.к. локальный lpu.id из БД ИС никак не связан с id в КС)
            try:
                units = proxy_client.listHospitals(infis_code=lpu.key)
            except WebFault, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__log(u'Ошибка: %s' % e)
                return False
            except TypeError, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__log(u'Ошибка: %s' % e)
                return False
            except Exception, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__log(u'Ошибка: %s' % e)
                return False
            else:
                for unit in units:
                    if not unit.name:
                        continue

                    address = getattr(unit, 'address', None)
                    if not address:
                        address = ''

                    if not getattr(unit, 'parentId', None) and not getattr(unit, 'parent_id', None):
                        self.session.add(LPU_Units(
                            lpuId=lpu.id,
                            orgId=unit.id,
                            name=unicode(unit.name),
                            address=address
                        ))
                        self.session.commit()
                        self.__log(u'%s: %s' % (unit.id, unit.name))
                        return_units.append(unit)

                self.__update_unit_parents(units, lpu)

        return return_units

    def __update_personal(self, lpu, lpu_units):
        """Обновляет информацию о врачах"""
        proxy = self.__get_proxy_address(lpu.proxy, lpu.protocol)
        result = False

        if proxy and lpu_units:
            proxy_client = Clients.provider(lpu.protocol, proxy)
            for unit in lpu_units:
                if unit.id:
                    try:
                        doctors = proxy_client.listDoctors(hospital_id=unit.id)
                    except WebFault, e:
                        logger.error(e, extra=logger_tags)
                        self.__log(u'Ошибка при получении списка врачей для %s: %s (%s)' % (unit.id, unit.name, e))
                        continue
                    except Exception, e:
                        logger.error(e, extra=logger_tags)
                        self.__log(u'Ошибка при получении списка врачей для %s: %s (%s)' % (unit.id, unit.name, e))
                        continue
                    else:
                        if doctors:
                            result = True
                            for doctor in doctors:
                                if doctor.firstName and doctor.lastName and doctor.patrName:
                                    speciality = self.__update_speciality(
                                        lpu_id=lpu.id,
                                        speciality=doctor.speciality.strip() if doctor.speciality else ''
                                    )
                                    post = self.__update_post(
                                        lpu_id=lpu.id,
                                        post=doctor.post.strip() if doctor.post else ''
                                    )
                                    if not speciality:
                                        continue

                                    key_epgu = self.session.query(Personal_KeyEPGU).filter(
                                        Personal_KeyEPGU.doctor_id == doctor.id,
                                        Personal_KeyEPGU.lpuId == lpu.id,
                                        Personal_KeyEPGU.orgId == unit.id
                                    ).first()

                                    if not key_epgu:
                                        key_epgu = Personal_KeyEPGU(
                                            doctor_id=doctor.id,
                                            lpuId=lpu.id,
                                            orgId=unit.id
                                        )
                                        self.session.add(key_epgu)

                                    personal = Personal(
                                        # key_epgu=key_epgu,
                                        doctor_id=doctor.id,
                                        lpuId=lpu.id,
                                        orgId=unit.id,
                                        FirstName=doctor.firstName,
                                        PatrName=doctor.patrName,
                                        LastName=doctor.lastName,
                                        office=getattr(doctor, 'office', None),
                                        snils=getattr(doctor, 'snils', None)
                                    )
                                    self.session.add(personal)
                                    self.session.commit()

                                    self.__add_personal_speciality(personal.id, speciality.id)
                                    self.__add_personal_post(personal.id, post.id)

                                    self.__log(u'%s: %s %s %s (%s)' % (doctor.id,
                                                                      doctor.firstName,
                                                                      doctor.lastName,
                                                                      doctor.patrName,
                                                                      doctor.speciality))
        return result

    def __update_speciality(self, **kwargs):
        speciality = self.session.query(Speciality).filter(Speciality.name == kwargs.get('speciality')).first()
        if not speciality:
            try:
                speciality = Speciality(name=kwargs.get('speciality'))
            except InvalidRequestError, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__failed_update(e)
                return False
            else:
                self.session.add(speciality)
                self.session.commit()
        self.__add_lpu_speciality(speciality_id=speciality.id, lpu_id=kwargs.get('lpu_id'))
        return speciality

    def __update_post(self, **kwargs):
        post = self.session.query(Post).filter(Post.name == kwargs.get('post')).first()
        if not post:
            try:
                post = Post(name=kwargs.get('post'))
            except InvalidRequestError, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__failed_update(e)
                return False
            else:
                self.session.add(post)
                self.session.commit()
        return post

    def __add_personal_speciality(self, doctor_id, speciality_id):
        self.session.add(Personal_Specialities(personal_id=doctor_id, speciality_id=speciality_id,))
        self.session.commit()

    def __add_personal_post(self, doctor_id, post_id):
        self.session.add(Personal_Posts(personal_id=doctor_id, post_id=post_id,))
        self.session.commit()

    def __add_lpu_speciality(self, **kwargs):
        if not self.session.query(LPU_Specialities).filter_by(**kwargs).first():
            try:
                self.session.add(LPU_Specialities(**kwargs))
                self.session.commit()
            except InvalidRequestError, e:
                print e
                logger.error(e, extra=logger_tags)
                self.__failed_update(e)
                return False
        return True

    def __failed_update(self, error=u""):
        self.session.rollback()
        # shutdown_session()
        if error:
            self.__log(u'Ошибка обновления: %s' % error)
            self.__log(u'----------------------------')
        return False

    def __success_update(self):
        self.session.commit()
        # shutdown_session()
        return True

    def update_data(self):
        """Основной метод, который производит вызов внутренних методов обновления данных в БД ИС"""
        # self.session.begin()
        # Update data in tables
        lpu_dw = DataWorker.provider('lpu', self.session)
        lpu_list = lpu_dw.get_list()
        if lpu_list:
            for lpu in lpu_list:
                if not lpu.id:
                    continue
                # TODO: возможно ли избавиться от удаления врачей?
                self.__clear_data(lpu)
                self.__log(u'Обновление ЛПУ: %s' % lpu.name)
                try:
                    lpu_units = self.__update_lpu_units(lpu)
                    if lpu_units:
                        if not self.__update_personal(lpu, lpu_units):
                            self.__failed_update(u'Пустой список врачей')
                            continue
                    else:
                        self.__failed_update(u'Не обнаружено подразделений')
                        continue
                    lpu.LastUpdate = time.mktime(datetime.datetime.now().timetuple())
                except WebFault, e:
                    print e
                    logger.error(e, extra=logger_tags)
                    self.__failed_update(e)
                except exceptions.UserWarning, e:
                    print e
                    logger.error(e, extra=logger_tags)
                    self.__failed_update(e)
                except urllib2.HTTPError, e:
                    print e
                    logger.error(e, extra=logger_tags)
                    self.__failed_update(e)
                    continue
                except IS_ConnectionError, e:
                    print e
                    logger.error(e, extra=logger_tags)
                    self.__failed_update(e.message)
                    continue
                except Exception, e:
                    print e
                    logger.error(e, extra=logger_tags)
                    self.__failed_update(e.message)
                else:
                    self.__success_update()
                    self.__log(u'Обновление прошло успешно!')
                    self.__log(u'----------------------------')
        return shutdown_session()
