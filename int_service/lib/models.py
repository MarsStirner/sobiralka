# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, String, Unicode, Text, UnicodeText, Enum, ForeignKey
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

class LPU(Base):
    '''
    Mapping for LPU table
    '''
    __tablename__ = 'lpu'

    id = Column(BigInteger, primary_key=True)
    name = Column(UnicodeText)
    address = Column(UnicodeText)
    key = Column(UnicodeText)
    proxy = Column(UnicodeText)
    email = Column(UnicodeText)
    kladr = Column(UnicodeText)
    OGRN = Column(String, length=15)
    OKATO = Column(String, length=15)
    LastUpdate = Column(Integer)
    phone = Column(String, length=20)
    schedule = Column(String, length=256)
    type = Column(String, length=32)
    protocol = Enum(['samson', 'intramed'])
    token = Column(String, length=45)


class LPU_Units(Base):
    '''
    Mapping for lpu_units table
    '''
    __tablename__ = 'lpu_units'

    id = Column(BigInteger, primary_key = True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'))
    name = Column(Unicode, length = 256)
    address = Column(Unicode, length = 256)

    lpu = relationship("LPU", backref=backref('lpu_units', order_by=id))


class UnitsParentForId(Base):
    '''
    Mapping for UnitsParentForId table
    '''
    __tablename__ = 'UnitsParentForId'

    id = Column(Integer, primary_key = True)
    LpuId = Column(String, ForeignKey('lpu.id'))
    OrgId = Column(String, ForeignKey('lpu.id'))
    ChildId = Column(String, ForeignKey('lpu_units.id'))
    name = Column(Unicode, length = 256)
    address = Column(Unicode, length = 256)

    lpu = relationship("LPU", backref=backref('lpu', order_by=id))
    org = relationship("LPU", backref=backref('lpu', order_by=id))
    child = relationship("LPU_Units", backref=backref('lpu_units', order_by=id))


class Enqueue(Base):
    '''
    Mapping for enqueue table
    '''
    __tablename__ = 'enqueue'

    id = Column(BigInteger, primary_key=True)
    Error = Column(String, length = 64)
    Data = Column(Text)

    def __init__(self, error, data):
        self.Error = error
        self.Data = data


class Personal(Base):
    '''
    Mapping for personal table
    '''
    __tablename__ = 'personal'

    id = Column(BigInteger, primary_key = True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'))
    orgId = Column(BigInteger, ForeignKey('lpu_units.id'))
    FirstName = Column(Unicode, length=32)
    LastName = Column(Unicode, length=32)
    PatrName = Column(Unicode, length=32)
#    TODO: replace to relationship on speciality_id=speciality.id
    speciality = Column(Unicode, length=64)
    keyEPGU = Column(String, length=45)

    lpu = relationship("LPU", backref=backref('personal', order_by=id))
    lpu_units = relationship("LPU_Units", backref=backref('personal', order_by=id))
