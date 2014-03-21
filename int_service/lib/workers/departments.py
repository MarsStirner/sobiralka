# -*- coding: utf-8 -*-
try:
    import json
except ImportError:
    import simplejson as json

from sqlalchemy import or_, and_
from sqlalchemy.orm.exc import NoResultFound

from admin.models import LPU, LPU_Units, Speciality, LPU_Specialities

from admin.database import Session
from ..utils import logger

logger_tags = dict(tags=['dataworker', 'IS'])


class LPU_UnitsWorker(object):
    """Класс для работы с информацией по подразделениям"""
    session = Session()
    # session.autocommit = True
    model = LPU_Units

    def __del__(self):
        self.session.close()

    def get_list(self, **kwargs):
        """Возвращает список подразделений

        Args:
            uid: массив uid подразделений (необязательный)
            lpu_id: массив id ЛПУ для фильтрации (необязательный)
            speciality: врачебная специальность для фильтрации подразделений (необязательный)

        """
        lpu_units_ids = kwargs.get('uid')
        speciality = kwargs.get('speciality')
        lpu_id = kwargs.get('lpu_id')

        # Prepare query for getting LPU_Units
#        fields = [LPU_Units.id, LPU_Units.lpuId, LPU_Units.name, LPU_Units.address,
#                  LPU.phone, LPU.token, LPU.key, UnitsParentForId.LpuId.label('parentId')]
        fields = [LPU_Units]
        filter = []
        _join = []
        or_list = []

        if speciality and isinstance(speciality, unicode):
            _join.extend([LPU, LPU_Specialities, Speciality])

        query_lpu_units = self.session.query(*fields)

        if _join:
            for i in _join:
                query_lpu_units = query_lpu_units.join(i)

        query_lpu_units = query_lpu_units.outerjoin(LPU_Units.lpu)
        # query_lpu_units = query_lpu_units.outerjoin(LPU_Units.parent, aliased=True)
        #.filter(LPU_Units.lpuId == UnitsParentForId.OrgId)

        if len(lpu_units_ids):
            for unit in lpu_units_ids:
                or_list.append(and_(LPU_Units.lpuId == unit[0], LPU_Units.orgId == unit[1]))
            query_lpu_units = query_lpu_units.filter(or_(*or_list))

        if speciality and isinstance(speciality, unicode):
            query_lpu_units = query_lpu_units.filter(Speciality.name == speciality)

        if lpu_id:
            query_lpu_units = query_lpu_units.filter(LPU_Units.lpuId == lpu_id)

        return query_lpu_units.group_by(LPU_Units.id).order_by(LPU_Units.name).all()

    def get_by_id(self, id):
        """
        Get LPU_Unit by id
        """
        try:
            result = self.session.query(LPU_Units).filter(LPU_Units.id == int(id)).one()
        except NoResultFound, e:
            logger.error(e, extra=logger_tags)
            print e
        else:
            return result
        return None
