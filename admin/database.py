from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from admin.models import Base

from settings import DB_CONNECT_STRING

engine = create_engine(DB_CONNECT_STRING, convert_unicode=True)
Session = scoped_session(sessionmaker(bind=engine))
Session2 = scoped_session(sessionmaker(bind=engine))
#Base = declarative_base()
Base.query = Session.query_property()


def init_task_session():
    task_engine = create_engine(DB_CONNECT_STRING, convert_unicode=True, pool_recycle=600)
    return scoped_session(sessionmaker(bind=task_engine))


def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    from admin.models import *
    # Session.begin()
    Base.metadata.create_all(bind=engine)
    Session.commit()


def shutdown_session(exception=None):
    Session.remove()
    Session2.remove()