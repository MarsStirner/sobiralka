# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Table, Integer, BigInteger, String, Unicode, Text, UnicodeText, Enum, ForeignKey, Boolean
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

class LPU(Base):
    """Mapping for LPU table"""
    __tablename__ = 'lpu'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(BigInteger, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    address = Column(UnicodeText, nullable=False)
    key = Column(Text, doc=u'ИНФИС код ЛПУ')
    proxy = Column(UnicodeText, doc=u'Прокси для запросов', nullable=False)
    email = Column(UnicodeText, doc='E-mail')
    kladr = Column(UnicodeText, doc=u'КЛАДР', nullable=True)
    OGRN = Column(String(15), doc=u'ОГРН', nullable=True)
    OKATO = Column(String(15), doc=u'ОКАТО', nullable=False)
    LastUpdate = Column(
        Integer,
        doc=u'Время последнего обновления специальностей для данного ЛПУ',
        nullable=False,
        default=0
    )
    phone = Column(String(20), doc=u'Телефон', nullable=True)
    schedule = Column(Unicode(256), doc=u'Расписание работы', nullable=False, default=u'')
    type = Column(Unicode(32), doc=u'Тип ЛПУ: (Поликлиника)')
    protocol = Column(Enum('samson', 'intramed', 'korus20', 'korus30'), nullable=False, default='korus30')
    token = Column(String(45), doc=u'Токен')


class LPU_Units(Base):
    """Mapping for lpu_units table"""
    __tablename__ = 'lpu_units'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(BigInteger, primary_key=True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'), index=True)
    orgId = Column(BigInteger, index=True)
    name = Column(Unicode(256))
    address = Column(Unicode(256))

    lpu = relationship("LPU", backref=backref('lpu_units', order_by=id))


# units_parents = Table("units_parents", Base.metadata,
#     Column("lpuid", BigInteger, ForeignKey("lpu.id")),
#     Column("orgid", BigInteger, ForeignKey("lpu.id")),
# )


class UnitsParentForId(Base):
    """Mapping for UnitsParentForId table"""
    __tablename__ = 'UnitsParentForId'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    LpuId = Column(BigInteger, ForeignKey('lpu.id'), index=True)
    OrgId = Column(BigInteger, ForeignKey('lpu_units.orgId'), index=True)
    ChildId = Column(BigInteger, ForeignKey('lpu_units.orgId'), index=True)

    lpu = relationship("LPU", backref=backref('lpu', order_by=id), foreign_keys=LpuId, primaryjoin=LPU.id==LpuId,)
    org = relationship("LPU_Units",
                       backref=backref('org', order_by=id),
                       foreign_keys=OrgId,
                       primaryjoin=LPU_Units.orgId==OrgId,)

    #TODO: проверка выборки parent
    child = relationship("LPU_Units",
        backref=backref('parent', order_by=id, uselist=False),
        foreign_keys=ChildId,
        primaryjoin="and_(LPU_Units.orgId==UnitsParentForId.ChildId, LPU_Units.lpuId==UnitsParentForId.LpuId)"
    )


class Enqueue(Base):
    """Mapping for enqueue table"""
    __tablename__ = 'enqueue'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(BigInteger, primary_key=True)
    Error = Column(String(64))
    Data = Column(Text)

    def __init__(self, error, data):
        self.Error = error
        self.Data = data


class Personal(Base):
    """Mapping for personal table"""
    __tablename__ = 'personal'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(BigInteger, primary_key=True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'), primary_key=True)
    orgId = Column(BigInteger, primary_key=True)
#    orgId = Column(BigInteger, ForeignKey('lpu_units.orgId'), primary_key=True)
    FirstName = Column(Unicode(32), nullable=False)
    LastName = Column(Unicode(32), nullable=False)
    PatrName = Column(Unicode(32), nullable=False)
#    TODO: replace to relationship on speciality_id=speciality.id
    speciality = Column(Unicode(64))
    keyEPGU = Column(String(45))

    lpu = relationship("LPU", backref=backref('personal', order_by=id))
#    lpu_units = relationship("LPU_Units", backref=backref('personal', order_by=id))
#    ForeignKeyConstraint(
#        ['personal.orgId', 'personal.lpuId'],
#        ['lpu_units.orgId', 'lpu_units.lpuId'],
#        use_alter=True,
#        name='personal_lpu_units_constraint'
#    )


class Speciality(Base):
    """Mapping for speciality table"""
    __tablename__ = 'speciality'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id'), index=True)
    speciality = Column(Unicode(64), nullable=False)
    nameEPGU = Column(Unicode(64))


class Regions(Base):
    """Mapping for regions table"""
    __tablename__ = 'regions'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=False)
    code = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True)

    __mapper_args__ = {'order_by': name}
