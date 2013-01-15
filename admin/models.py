# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Table, Integer, BigInteger, String, Unicode, Text, UnicodeText, Enum, ForeignKey
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

class LPU(Base):
    """Mapping for LPU table"""
    __tablename__ = 'lpu'

    id = Column(BigInteger, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    address = Column(UnicodeText, nullable=False)
    key = Column(UnicodeText, doc='ServerId')
    proxy = Column(UnicodeText, doc=u'Прокси для запросов', nullable=False)
    email = Column(UnicodeText, doc='E-mail')
    kladr = Column(UnicodeText, doc=u'КЛАДР', nullable=False)
    OGRN = Column(String(15), doc=u'ОГРН', nullable=False)
    OKATO = Column(String(15), doc=u'ОКАТО', nullable=False)
    LastUpdate = Column(
        Integer,
        doc=u'Время последнего обновления специальностей для данного ЛПУ',
        nullable=False,
        default=0
    )
    phone = Column(String(20), doc=u'Телефон', nullable=False)
    schedule = Column(Unicode(256), doc=u'Расписание работы')
    type = Column(Unicode(32), doc=u'Тип ЛПУ: (Поликлиника)')
    protocol = Column(Enum(['samson', 'intramed', 'korus20', 'korus30']), nullable=False, default='korus30')
    token = Column(String(45), doc=u'Токен')


class LPU_Units(Base):
    """Mapping for lpu_units table"""
    __tablename__ = 'lpu_units'

    id = Column(BigInteger, primary_key = True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'))
    orgId = Column(BigInteger)
    name = Column(Unicode(256))
    address = Column(Unicode(256))

    lpu = relationship("LPU", backref=backref('lpu_units', order_by=id))


units_parents = Table("units_parents", Base.metadata,
    Column("lpuid", BigInteger, ForeignKey("lpu.id")),
    Column("orgid", BigInteger, ForeignKey("lpu.id")),
)
class UnitsParentForId(Base):
    """Mapping for UnitsParentForId table"""
    __tablename__ = 'UnitsParentForId'

    id = Column(Integer, primary_key = True)
    LpuId = Column(BigInteger, ForeignKey('lpu.id'))
    OrgId = Column(BigInteger, ForeignKey('lpu.id'))
    ChildId = Column(BigInteger)

    lpu = relationship("LPU", backref=backref('lpu', order_by=id), foreign_keys=LpuId, primaryjoin=LPU.id==LpuId,)
    org = relationship("LPU", backref=backref('org', order_by=id), foreign_keys=OrgId, primaryjoin=LPU.id==OrgId,)

    #TODO: проверка выборки parent
    child = relationship("LPU_Units",
        backref=backref('parent', order_by=id),
        foreign_keys=ChildId,
        primaryjoin="and_(LPU_Units.orgId==UnitsParentForId.ChildId, LPU_Units.lpuId==UnitsParentForId.OrgId)"
    )


class Enqueue(Base):
    """Mapping for enqueue table"""
    __tablename__ = 'enqueue'

    id = Column(BigInteger, primary_key=True)
    Error = Column(String(64))
    Data = Column(Text)

    def __init__(self, error, data):
        self.Error = error
        self.Data = data


class Personal(Base):
    """Mapping for personal table"""
    __tablename__ = 'personal'

    id = Column(BigInteger, primary_key=True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'), primary_key=True)
    orgId = Column(BigInteger, ForeignKey('lpu_units.orgId'), primary_key=True)
    FirstName = Column(Unicode(32), nullable=False)
    LastName = Column(Unicode(32), nullable=False)
    PatrName = Column(Unicode(32), nullable=False)
#    TODO: replace to relationship on speciality_id=speciality.id
    speciality = Column(Unicode(64))
    keyEPGU = Column(String(45))

    lpu = relationship("LPU", backref=backref('personal', order_by=id))
    lpu_units = relationship("LPU_Units", backref=backref('personal', order_by=id))


class Speciality(Base):
    """Mapping for speciality table"""
    __tablename__ = 'speciality'

    id = Column(Integer(10), primary_key=True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'))
    speciality = Column(Unicode(64), nullable=False)
    nameEPGU = Column(Unicode(64))