#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from database import Session
from models import Personal, LPU
import csv
session = Session()


def _get_lpu_dbs():
    lpu_dbs = list()
    with open('lpu_db.csv', 'rb') as csvfile:
        data = csv.reader(csvfile, delimiter='\t', quotechar='|')
        for row in data:
            key = row[0]
            if len(key) == 1:
                key = '000{0}'.format(key)
            lpu_dbs.append(dict(key=key, ip=row[1], db_name=row[2].lower()))
    return lpu_dbs


def _get_lpu_session(db):
    DB_CONNECT_STRING = 'mysql://%s:%s@%s:%s/%s?charset=utf8' % ('tmis', 'bdsvai_20', db['ip'], 3306, db['db_name'])
    engine = create_engine(DB_CONNECT_STRING, convert_unicode=True, pool_recycle=600)
    lpu_session = scoped_session(sessionmaker(bind=engine))
    return lpu_session


def _get_lpu_snils(lpu_session):
    res = list()
    result = lpu_session.execute('SELECT id, snils FROM Person WHERE deleted=0 AND snils')
    for row in result.fetchall():
        res.append(row)
    return res


def _get_lpu_id(infis):
    lpu = session.query(LPU).filter(LPU.key == infis).first()
    if lpu:
        return lpu.id
    return None


def _get_person(key, doctor_id):
    return session.query(Personal).filter(Personal.lpu.key == key, Personal.doctor_id == doctor_id).first()


def update_snils():
    dbs = _get_lpu_dbs()
    for db in dbs:
        lpu_session = _get_lpu_session(db)
        lpu_snils = _get_lpu_snils(lpu_session)
        if lpu_snils:
            for snils in lpu_snils:
                doctor = _get_person(db['key'], snils['id'])
                if doctor and not doctor.snils:
                    doctor.snils = snils.replace('-', '').replace(' ')
                    session.commit()

if __name__ == "__main__":
    update_snils()