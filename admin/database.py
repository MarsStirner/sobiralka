from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from admin.models import Base

from settings import DB_CONNECT_STRING

engine = create_engine(DB_CONNECT_STRING, convert_unicode=True, pool_recycle=300)
Session = scoped_session(sessionmaker(bind=engine))
#Base = declarative_base()
Base.query = Session.query_property()


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from admin.models import LPU, LPU_Units, Enqueue, Personal, Speciality, UnitsParentForId
    Base.metadata.create_all(bind=engine)
    Session.commit()


def shutdown_session(exception=None):
    Session.close()
    Session.remove()