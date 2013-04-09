# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Table, Integer, BigInteger, String, Unicode, Text, UnicodeText, Enum, ForeignKey, Boolean
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import ClauseList

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
    token = Column(String(45), doc=u'Токен ЕПГУ')
    keyEPGU = Column(String(45), doc=u'ID ЛПУ на ЕПГУ')


class LPU_Units(Base):
    """Mapping for lpu_units table"""
    __tablename__ = 'lpu_units'

    id = Column(BigInteger, primary_key=True)
    lpuId = Column(BigInteger, ForeignKey('lpu.id', ondelete='CASCADE'))
    orgId = Column(BigInteger)
    name = Column(Unicode(256))
    address = Column(Unicode(256))

    __table_args__ = (Index('lpu_org', lpuId, orgId), {'mysql_engine': 'InnoDB'})

    lpu = relationship(LPU, backref=backref('lpu_units', order_by=id))


class UnitsParentForId(Base):
    """Mapping for UnitsParentForId table"""
    __tablename__ = 'UnitsParentForId'

    LpuId = Column(BigInteger, ForeignKey(LPU.id, ondelete='CASCADE'), primary_key=True)
    OrgId = Column(BigInteger, primary_key=True)
    ChildId = Column(BigInteger, primary_key=True)

    __table_args__ = (ForeignKeyConstraint([LpuId, OrgId], [LPU_Units.lpuId, LPU_Units.orgId]),
                      {'mysql_engine': 'InnoDB'})

    lpu = relationship(LPU)

    org = relationship(
        LPU_Units,
        primaryjoin='and_(LPU_Units.orgId==UnitsParentForId.OrgId, LPU_Units.lpuId==UnitsParentForId.LpuId)',
    )

    children = relationship(
        LPU_Units,
        backref=backref('parent', uselist=False),
        primaryjoin="and_(LPU_Units.orgId==UnitsParentForId.ChildId, LPU_Units.lpuId==UnitsParentForId.LpuId)"
    )


class Enqueue(Base):
    """Mapping for enqueue table"""
    __tablename__ = 'enqueue'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(BigInteger, primary_key=True)
    Error = Column(String(64))
    Data = Column(Text)
    patient_id = Column(BigInteger)
    ticket_id = Column(BigInteger)
    keyEPGU = Column(String(100))


class EPGU_Speciality(Base):
    """Mapping for epgu_specialities table"""
    __tablename__ = 'epgu_speciality'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=False, unique=True)
    keyEPGU = Column(String(45))

    def __unicode__(self):
        return self.name


class EPGU_Service_Type(Base):
    """Mapping for epgu_service_type table"""
    __tablename__ = 'epgu_service_type'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(150), nullable=False)
    epgu_speciality_id = Column(Integer, ForeignKey(EPGU_Speciality.id))
    recid = Column(String(20))
    code = Column(Unicode(20))
    keyEPGU = Column(String(45))
    epgu_speciality = relationship(EPGU_Speciality, backref=backref('epgu_service_type'), lazy='joined')

    __mapper_args__ = {'order_by': name}

    def __unicode__(self):
        return self.name


class EPGU_Reservation_Type(Base):
    """Mapping for epgu_service_type table"""
    __tablename__ = 'epgu_reservation_type'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(50), nullable=False)
    code = Column(String(50), nullable=False)
    keyEPGU = Column(String(45))


class EPGU_Payment_Method(Base):
    """Mapping for epgu_service_type table"""
    __tablename__ = 'epgu_payment_method'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(150), nullable=False)
    default = Column(Boolean, default=False)
    keyEPGU = Column(String(45))


class Speciality(Base):
    """Mapping for speciality table"""
    __tablename__ = 'speciality'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=False, unique=True)
    epgu_speciality_id = Column(Integer, ForeignKey('epgu_speciality.id'), nullable=True, index=True)
    epgu_speciality = relationship(EPGU_Speciality, lazy='joined')
    epgu_service_type_id = Column(Integer, ForeignKey('epgu_service_type.id'), nullable=True, index=True)
    epgu_service_type = relationship(EPGU_Service_Type, lazy='joined',)

    __mapper_args__ = {'order_by': name}


class Personal(Base):
    """Mapping for personal table"""
    __tablename__ = 'personal'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(BigInteger, primary_key=True)
    doctor_id = Column(BigInteger, index=True)
    lpuId = Column(BigInteger, ForeignKey(LPU.id), index=True)
    orgId = Column(BigInteger, index=True)
#    orgId = Column(BigInteger, ForeignKey('lpu_units.orgId'), primary_key=True)
    FirstName = Column(Unicode(32), nullable=False)
    LastName = Column(Unicode(32), nullable=False)
    PatrName = Column(Unicode(32), nullable=False)
    office = Column(Unicode(8), nullable=True)
    keyEPGU = Column(String(45))

    lpu = relationship(LPU, backref=backref('personal', order_by=id))
    speciality = relationship(Speciality, secondary='personal_speciality', backref=backref('personal'), lazy='joined')
    UniqueConstraint(doctor_id, lpuId, orgId)

#    lpu_units = relationship("LPU_Units", backref=backref('personal', order_by=id))
#    ForeignKeyConstraint(
#        ['personal.orgId', 'personal.lpuId'],
#        ['lpu_units.orgId', 'lpu_units.lpuId'],
#        use_alter=True,
#        name='personal_lpu_units_constraint'
#    )


# Personal_Specialities = Table(
#     'personal_speciality',
#     Base.metadata,
#     Column('personal_id', BigInteger, ForeignKey('personal.id', ondelete='CASCADE'), primary_key=True),
#     Column('speciality_id', Integer, ForeignKey('speciality.id', ondelete='CASCADE'), primary_key=True)
# )

class Personal_Specialities(Base):
    """Mapping for many-to-many relations between Personal and Specialities"""
    __tablename__ = 'personal_speciality'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    personal_id = Column(BigInteger, ForeignKey('personal.id', ondelete='CASCADE'), primary_key=True)
    speciality_id = Column(Integer, ForeignKey('speciality.id', ondelete='CASCADE'), primary_key=True)

    UniqueConstraint(personal_id, speciality_id)

    personal = relationship(Personal)
    speciality = relationship(Speciality, lazy='joined')


class LPU_Specialities(Base):
    """Mapping for many-to-many relations between LPU and Specialities"""
    __tablename__ = 'lpu_speciality'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    lpu_id = Column(BigInteger, ForeignKey(LPU.id, ondelete='CASCADE'), primary_key=True)
    speciality_id = Column(Integer, ForeignKey(Speciality.id, ondelete='CASCADE'), primary_key=True)

    UniqueConstraint(lpu_id, speciality_id)

    lpu = relationship(LPU)
    speciality = relationship(Speciality)


class Regions(Base):
    """Mapping for regions table"""
    __tablename__ = 'regions'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=False)
    code = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True)

    __mapper_args__ = {'order_by': name}