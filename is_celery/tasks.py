# -*- coding: utf-8 -*-
from __future__ import absolute_import

import exceptions
from celery import group, chain
from celery.signals import task_postrun
from celery.utils.log import get_task_logger
from is_celery.celery_init import celery
from int_service.lib.dataworker import UpdateWorker, DataWorker
from admin.database import init_task_session
from admin.models import LPU, Personal, Personal_KeyEPGU

task_logger = get_task_logger(__name__)
Task_Session = init_task_session()
db_session = Task_Session()


def remove_session():
    Task_Session.remove()


class SqlAlchemyTask(celery.Task):
    """An abstract Celery Task that ensures that the connection to the
    database is closed on task completion"""
    abstract = True

    def after_return(self, *args, **kwargs):
        remove_session()


# SYNC SCHEDULE TASKS
@celery.task(base=SqlAlchemyTask)
def appoint_patients(parent_task_returns, auth_token, doctor):
    print parent_task_returns
    if not parent_task_returns:
        return None
    patient_slots = parent_task_returns
    if not patient_slots:
        return None
    epgu_dw = DataWorker.provider('epgu', db_session, auth_token=auth_token)
    epgu_dw.appoint_patients(patient_slots, doctor)
    return epgu_dw.msg


@celery.task(base=SqlAlchemyTask)
def doctor_schedule_task(doctor, auth_token):
    epgu_dw = DataWorker.provider('epgu', db_session, auth_token=auth_token)
    return epgu_dw.doctor_schedule_task(doctor, auth_token)


@celery.task(base=SqlAlchemyTask)
def lpu_schedule_task(hospital_id, auth_token):
    epgu_doctors = db_session.query(Personal).filter(Personal.lpuId == hospital_id).filter(
        Personal.key_epgu.has(Personal_KeyEPGU.epgu2_id != None)
    ).all()
    if epgu_doctors:
        group(
            [chain(
                doctor_schedule_task.s(doctor, auth_token),
                # link_schedule.s(hospital_dict, doctor.key_epgu.keyEPGU),
                # activate_location.s(hospital_dict, doctor.key_epgu.keyEPGU).set(countdown=5),
                appoint_patients.s(auth_token, doctor).set(countdown=5)
            ) for doctor in epgu_doctors])()
    # shutdown_session()


@celery.task(base=SqlAlchemyTask)
def lpu_tickets_task(hospital_id, auth_token):
    epgu_doctors = db_session.query(Personal).filter(Personal.lpuId == hospital_id).filter(
        Personal.key_epgu.has(Personal_KeyEPGU.epgu2_id != None)
    ).all()
    if epgu_doctors:
        epgu_dw = DataWorker.provider('epgu', db_session, auth_token=auth_token)
        group([appoint_patients.s((None, epgu_dw.get_doctor_tickets(doctor)), auth_token, doctor)
               for doctor in epgu_doctors])()


@celery.task(base=SqlAlchemyTask)
def sync_tickets_task():
    lpu_list = (db_session.query(LPU).
                filter(LPU.epgu2_token != '',
                       LPU.epgu2_token != None).
                all())
    if lpu_list:
        res = group([
            lpu_tickets_task.s(lpu.id, lpu.epgu2_token) for lpu in lpu_list])()
        # print res.get()
    else:
        # self.__log(u'Нет ни одного ЛПУ, синхронизированного с ЕПГУ')
        return False


@celery.task(base=SqlAlchemyTask)
def sync_schedule_task():
    lpu_list = (db_session.query(LPU).
                filter(LPU.epgu2_token != '',
                       LPU.epgu2_token != None).
                all())
    if lpu_list:
        res = group([
            lpu_schedule_task.s(
                lpu.id,
                auth_token=lpu.epgu2_token
            ) for lpu in lpu_list])()
        # print res.get()
        # print self.msg
    else:
        # self.__log(u'Нет ни одного ЛПУ, синхронизированного с ЕПГУ')
        return False


@celery.task(base=SqlAlchemyTask)
def sync_locations():
    epgu_dw = DataWorker.provider('epgu', db_session)
    epgu_dw.sync_locations()


@task_postrun.connect
def close_session(*args, **kwargs):
    db_session.close()
    remove_session()


@celery.task(base=SqlAlchemyTask)
def clear_broker_messages():
    db_session.execute('DELETE FROM kombu_message WHERE visible=0')
    db_session.commit()


@celery.task(base=SqlAlchemyTask)
def epgu_send_lpu_tickets(hospital_id, auth_token):
    epgu_dw = DataWorker.provider('epgu', Task_Session(), auth_token=auth_token)
    try:
        epgu_dw.send_new_tickets(hospital_id)
    except exceptions.Exception, e:
        print e


@celery.task(base=SqlAlchemyTask)
def epgu_send_new_tickets():
    lpu_list = (db_session.query(LPU).
                filter(LPU.epgu2_token != '',
                       LPU.epgu2_token != None).
                all())
    if lpu_list:
        res = group([
            epgu_send_lpu_tickets.s(
                lpu.id,
                auth_token=lpu.epgu2_token
            ) for lpu in lpu_list])()
    else:
        # self.__log(u'Нет ни одного ЛПУ, синхронизированного с ЕПГУ')
        return False


# UPDATE TASKS
@celery.task(base=SqlAlchemyTask)
def update_db():
    data_worker = UpdateWorker(db_session)
    data_worker.update_data()

clear_broker_messages()