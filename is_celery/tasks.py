# -*- coding: utf-8 -*-
from __future__ import absolute_import

from celery import group, chain
from celery.signals import task_postrun
from celery.utils.log import get_task_logger
from is_celery.celery_init import celery
from int_service.lib.dataworker import EPGUWorker, UpdateWorker
from admin.database import Tasks_Session as db_session, shutdown_session
from admin.models import LPU, Personal, Personal_KeyEPGU

task_logger = get_task_logger(__name__)


# SYNC SCHEDULE TASKS
@celery.task
def appoint_patients(parent_task_returns, hospital, doctor):
    if not parent_task_returns:
        return None
    rules, patient_slots = parent_task_returns
    if not patient_slots:
        return None
    epgu_dw = EPGUWorker()
    epgu_dw.appoint_patients(patient_slots, hospital, doctor)
    return epgu_dw.msg


@celery.task
def activate_location(parent_task_returns, hospital, location_id):
    if not parent_task_returns:
        return None
    epgu_dw = EPGUWorker()
    epgu_dw.activate_location(hospital, location_id)
    return parent_task_returns


@celery.task
def link_schedule(parent_task_returns, hospital, location_id):
    rules, busy_by_patients = parent_task_returns
    if not rules:
        return None
    epgu_dw = EPGUWorker()
    epgu_dw.link_schedule(rules, hospital, location_id)
    return parent_task_returns


@celery.task
def doctor_schedule_task(doctor, hospital_dict):
    epgu_dw = EPGUWorker()
    return epgu_dw.doctor_schedule_task(doctor, hospital_dict)


@celery.task
def lpu_schedule_task(hospital_id, hospital_dict):
    epgu_doctors = db_session.query(Personal).filter(Personal.lpuId == hospital_id).filter(
        Personal.key_epgu.has(Personal_KeyEPGU.keyEPGU != None)
    ).all()
    if epgu_doctors:
        group(
            [chain(
                doctor_schedule_task.s(doctor, hospital_dict),
                link_schedule.s(hospital_dict, doctor.key_epgu.keyEPGU),
                activate_location.s(hospital_dict, doctor.key_epgu.keyEPGU).set(countdown=5),
                appoint_patients.s(hospital_dict, doctor).set(countdown=5)
            ) for doctor in epgu_doctors])()


@celery.task
def sync_schedule_task():
    lpu_list = (db_session.query(LPU).
                filter(LPU.keyEPGU != '',
                       LPU.keyEPGU != None,
                       LPU.token != '',
                       LPU.token != None).
                all())
    if lpu_list:
        res = group([
            lpu_schedule_task.s(
                lpu.id,
                dict(auth_token=lpu.token, place_id=lpu.keyEPGU)
            ) for lpu in lpu_list])()
        # print res.get()
        # print self.msg
    else:
        # self.__log(u'Нет ни одного ЛПУ, синхронизированного с ЕПГУ')
        return False


@celery.task
def sync_locations():
    epgu_dw = EPGUWorker()
    epgu_dw.sync_locations()


@task_postrun.connect
def close_session(*args, **kwargs):
    shutdown_session()


# UPDATE TASKS
@celery.task
def update_db():
    data_worker = UpdateWorker()
    data_worker.update_data()