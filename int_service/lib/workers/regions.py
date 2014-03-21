# -*- coding: utf-8 -*-
from admin.database import Session
from admin.models import Regions


class RegionsWorker(object):
    """Класс для работы с информацией по регионам"""
    session = Session()
    # session.autocommit = True
    model = Regions

    def __del__(self):
        self.session.close()

    def get_list(self):
        """Возвращает список регионов"""
        return self.session.query(Regions).filter(Regions.is_active == True).order_by(Regions.name).all()