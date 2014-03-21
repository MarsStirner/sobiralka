# -*- coding: utf-8 -*-
import exceptions
import datetime

try:
    import json
except ImportError:
    import simplejson as json

from sqlalchemy import or_, and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.scoping import ScopedSession
from admin.models import Enqueue
from ..service_clients import Clients
from ..is_exceptions import exception_by_code

from admin.database import Session, init_task_session, shutdown_session
from ..utils import logger
from ..dataworker import DataWorker

logger_tags = dict(tags=['dataworker', 'IS'])


class EnqueueWorker(object):
    # session.autocommit = True
    model = Enqueue
    SCHEDULE_DAYS_DELTA = 60  # 14
    #TODO: вернуть меньшее количество дней, но на стороне сайта и ТК передавать даты начала и окончания

    def __init__(self, session=None):
        if session is not None and isinstance(session, ScopedSession):
            self.session = session
        else:
            self.session = Session()

    def __del__(self):
        self.session.close()

    def get_info(self, **kwargs):
        """Возвращает информацию о расписании

        Args:
            hospitalUid: uid ЛПУ, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            doctorUid: uid врача (обязательный)
            speciality: наименование врачебной специальности (необязательный)
            hospitalUidFrom: uid ЛПУ, из которого производилась запись (необязательный)

        """
        result = {}

        hospital_uid = kwargs.get('hospitalUid', '')
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        if isinstance(hospital_uid, list) and len(hospital_uid) > 1:
            lpu_dw = DataWorker.provider('lpu')
            lpu = lpu_dw.get_by_id(hospital_uid[0])
        else:
            shutdown_session()
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError

        if 'doctorUid' in kwargs:
            doctor_uid = int(kwargs.get('doctorUid'))
        else:
            shutdown_session()
            logger.error(exceptions.KeyError(), extra=logger_tags)
            raise exceptions.KeyError

        speciality = kwargs.get('speciality')
        if not speciality:
            personal_dw = DataWorker.provider('personal')
            doctor = personal_dw.get_doctor(doctor_id=doctor_uid, lpu_unit=hospital_uid)
            if doctor:
                speciality = doctor.speciality[0].name

        hospital_uid_from = kwargs.get('hospitalUidFrom')
        if not hospital_uid_from:
            hospital_uid_from = 0

        start, end = self.__get_dates_period(kwargs.get('startDate'), kwargs.get('endDate'))

        proxy_client = Clients.provider(lpu.protocol, lpu.proxy.split(';')[0])
        params = {
            'hospital_uid': hospital_uid,
            'doctor_uid': doctor_uid,
            'start': start,
            'end': end,
            'speciality': speciality,
            'hospital_uid_from': hospital_uid_from,
            'server_id': lpu.key
        }
        result = proxy_client.getScheduleInfo(**params)
        shutdown_session()
        return result

    def get_closest_tickets(self, hospitalUid, doctors, start=None):
        result = list()
        hospital_uid = hospitalUid
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        if isinstance(hospital_uid, list) and len(hospital_uid) > 1:
            lpu_id = hospital_uid[0]
        else:
            shutdown_session()
            raise exceptions.ValueError
        lpu_dw = DataWorker.provider('lpu')
        lpu = lpu_dw.get_by_id(lpu_id)
        proxy_client = Clients.provider(lpu.protocol, lpu.proxy.split(';')[0])
        method = 'get_closest_free_ticket'
        if hasattr(proxy_client, method) and callable(getattr(proxy_client, method)):
            for doctor_id in doctors:
                try:
                    ticket = proxy_client.get_closest_free_ticket(doctor_id, start)
                except Exception, e:
                    logger.error(e, extra=logger_tags)
                    print e
                else:
                    #result[doctor_id] = ticket
                    result.append(ticket)
        return dict(tickets=result)

    def __get_dates_period(self, start, end):
        if not start:
            start = datetime.date.today()
        if not end:
            end = (start + datetime.timedelta(days=self.SCHEDULE_DAYS_DELTA))
        return start, end

    def __get_tickets_ge_id(self, id, hospital_uid=None):
        tickets = []
        for item in self.session.query(Enqueue).filter(
            Enqueue.DataType == '0',
            Enqueue.id > id,
            Enqueue.Error == '100 ok',
            Enqueue.status == 0
        ):
            data = json.load(item.Data)
            if hospital_uid and hospital_uid == data['hospitalUid'] or hospital_uid is None:
                tickets.append({
                    'id': item.id,
                    'data': data,
                    'error': item.error,
                })
        return tickets

    def get_by_id(self, id):
        """Возвращает талончик по id

        Args:
            id: id талончика

        """
        try:
            result = self.session.query(Enqueue).filter(Enqueue.id == int(id)).one()
        except NoResultFound, e:
            print e
            logger.error(e, extra=logger_tags)
        else:
            return result
        return None

    def get_ticket_status(self, **kwargs):
        """Возвращает статус талончика

        Args:
            hospitalUid: uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            ticketUid: uid талончика (обязательный), строка вида 'ticket_id/patient_id'
            lastUid: id талончика, начиная с которого необходимо сделать выборку информации о талончиках,
                если передан, то ticketUid игнорируется (необязательный)

        """
        result = dict()
        result['ticketInfo'] = []
        hospital_uid = kwargs.get('hospitalUid', '').split('/')
        ticket_uid = kwargs.get('ticketUid')
        if hospital_uid and ticket_uid:
            if len(hospital_uid) > 1:
                if hospital_uid[1]:
                    # It's lpu_unit, work with LPU_UnitsWorker
                    dw = DataWorker.provider('lpu_units')
                    lpu_info = dw.get_by_id(hospital_uid[1])
                    lpu_address = lpu_info.address
                    lpu_name = lpu_info.name + '(' + lpu_info.lpu.name + ')'
                    proxy_client = Clients.provider(lpu_info.lpu.protocol, lpu_info.lpu.proxy.split(';')[0])
                    server_id = lpu_info.lpu.key
                else:
                    # It's lpu, works with LPUWorker
                    dw = DataWorker.provider('lpu')
                    lpu_info = dw.get_by_id(hospital_uid[0])
                    lpu_address = lpu_info.address
                    lpu_name = lpu_info.name
                    proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
                    server_id = lpu_info.key
            else:
                shutdown_session()
#                raise exceptions.AttributeError
                return result
        else:
            shutdown_session()
            logger.error(exceptions.KeyError(), extra=logger_tags)
            raise exceptions.KeyError

        last_uid = kwargs.get('lastUid')

        if last_uid:
            tickets = self.__get_tickets_ge_id(last_uid, hospital_uid)
        else:
            if isinstance(ticket_uid, list):
                tickets = ticket_uid
            else:
                tickets = [ticket_uid, ]

        doctor_dw = DataWorker.provider('personal')
        if tickets:
            for ticket in tickets:
                # TODO: разнести по отдельным методам
                if isinstance(ticket, dict):
                    # Working on case where kwargs['lastUid']
                    ticket_data = ticket['data']

                    # For low code dependence get current hospital_uid
                    _hospital_uid = ticket_data['hospital_uid'].split('/')

                    doctor = doctor_dw.get_doctor(lpu_unit=_hospital_uid, doctor_id=ticket_data['doctorUid'])
                    result['ticketInfo'].append({
                        'id': ticket['id'],
                        'ticketUid': ticket_data['ticketUid'],
                        'hospitalUid': ticket_data['hospitalUid'],
                        'doctorUid': ticket_data['doctorUid'],
                        'doctor': {
                            'firstName': doctor.get('firstName', ''),
                            'patronymic': doctor.get('patronymic', ''),
                            'lastName': doctor.get('lastName', ''),
                        },
                        'person': {
                            'firstName': '',
                            'patronymic': '',
                            'lastName': '',
                        },
                        'status': 'forbidden',
                        'timeslotStart': datetime.datetime.strptime(ticket_data['timeslotStart'], '%Y-%m-%dT%H:%M:%S'),
                        'comment': str(exception_by_code(ticket.get('Error'))),
                        'location': lpu_name + " " + lpu_address,
                    })

                else:

                    ticket_uid, patient_id = ticket.split('/')

                    queue_info = proxy_client.getPatientQueue({'serverId': server_id, 'patientId': patient_id})
                    patient_info = proxy_client.getPatientInfo({'serverId': server_id, 'patientId': patient_id})

                    for ticket_info in queue_info:
                        if ticket_info.queueId == ticket_uid:
                            doctor = doctor_dw.get_doctor(lpu_unit=hospital_uid, doctor_id=ticket_info['personId'])

                            if ticket_info['enqueuePersonId']:
                                # TODO: проверить действительно ли возвращаемый enqueuePersonId - это office
                                office = ticket_info['enqueuePersonId']
                            else:
                                work_times = proxy_client.getWorkTimeAndStatus({
                                    'serverId': server_id,
                                    'personId': ticket_info['personId'],
                                    'date': ticket_info['enqueueDate'],
                                })
                                if work_times:
                                    office = work_times[0].get('office')

                            _ticket_date = datetime.datetime.strptime(
                                ticket_info['date'] + ticket_info['time'], '%Y-%m-%d %H:%M:%S'
                            )

                            document = self.__get_ticket_print({
                                'name': lpu_name,
                                'address': lpu_address,
                                'fio': ' '.join((
                                    patient_info['lastName'],
                                    patient_info['firstName'][0:1] + '.',
                                    patient_info['patrName'][0:1] + '.'
                                )),
                                'person': ' '.join((
                                    doctor.get('lastName', ''),
                                    doctor.get('firstName', ''),
                                    doctor.get('patronymic', '')
                                )),
                                'date_time': _ticket_date,
                                'office': office,
                            })

                            result['ticketInfo'].append({
                                'id': '',
                                'ticketUid': ticket,
                                'hospitalUid': hospital_uid,
                                'doctorUid': ticket_info['personId'],
                                'doctor': {
                                    'firstName': doctor.get('firstName', ''),
                                    'patronymic': doctor.get('patronymic', ''),
                                    'lastName': doctor.get('lastName', ''),
                                },
                                'person': {
                                    'firstName': patient_info.get('firstName'),
                                    'patronymic': patient_info.get('patrName'),
                                    'lastName': patient_info.get('lastName'),
                                },
                                'status': 'accepted',
                                'timeslotStart': _ticket_date,
#                                'comment': exception_by_code(ticket_info.Error),
                                'location': 'кабинет:' + office + ' ' + lpu_address,
                                'printableDocument': {
                                    'printableVersionTitle': 'Талон',
                                    'printableVersion': document.encode('base64'),
                                    'printableVersionMimeType': 'application/pdf',
                                }
                            })

        shutdown_session()
        return result

    def __prepare_tickets_info(self, hospital_uid, lpu_info, patient, tickets):
        proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
        doctor_dw = DataWorker.provider('personal')
        result = list()
        for ticket in tickets:
            date_time = getattr(ticket, 'dateTime')
            doctor = doctor_dw.get_doctor(lpu_unit=hospital_uid, doctor_id=getattr(ticket, 'personId', None))
            work_times = proxy_client.getWorkTimeAndStatus(personId=getattr(ticket, 'personId'),
                                                           date=date_time.date())
            office = u'-'
            if work_times:
                office = work_times[0].get('office')

            result.append({
                'id': '',
                'ticketUid': '{0}/{1}'.format(getattr(ticket, 'queueId'), getattr(patient, 'patientId')),
                'hospitalUid': '{0}/{1}'.format(*hospital_uid),
                'doctorUid': getattr(ticket, 'personId'),
                'doctor': {
                    'name': {
                        'firstName': doctor.FirstName,
                        'patronymic': doctor.PatrName,
                        'lastName': doctor.LastName
                    },
                    'uid': getattr(ticket, 'personId'),
                    'speciality': doctor.speciality[0].name,
                    'hospitalUid': '{0}/{1}'.format(doctor.lpuId, doctor.orgId)
                },
                'person': {
                    'firstName': '',
                    'patronymic': '',
                    'lastName': '',
                },
                'timeslotStart': date_time,
#               'comment': exception_by_code(ticket_info.Error),
                'location': u'{0} ({1}), кабинет: {2}'.format(lpu_info.name, lpu_info.address, office)
            })
        return result

    def patient_tickets(self, **kwargs):
        """Талончики пациента

        Args:
            person: { ФИО пациента (обязательный)
                'firstName'
                'lastName'
                'patronymic'
            }
            hospitalUid:
                uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            birthday: дата рождения пациента (необязательный)
            sex: пол (необязательный)
            hospitalUidFrom: uid ЛПУ, с которого производится запись (необязательный), используется для записи между ЛПУ

        """
        hospital_uid = kwargs.get('hospitalUid', '')
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        birthday = kwargs.get('birthday')
        patient = kwargs.get('person')
        sex = kwargs.get('sex')
        document_obj = kwargs.get('document')
        document = dict()
        if document_obj:
            if document_obj.client_id:
                document['client_id'] = str(document_obj.client_id)
            if document_obj.policy_type:
                document['policy_type'] = str(document_obj.policy_type)
            if document_obj.document_code:
                document['document_code'] = str(document_obj.document_code)
            if document_obj.series:
                document['serial'] = document_obj.series
            else:
                document['serial'] = ''
            if document_obj.number:
                document['number'] = document_obj.number

        if len(hospital_uid) > 1:
            dw = DataWorker.provider('lpu')
            lpu_info = dw.get_by_id(hospital_uid[0])
            proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
        else:
            shutdown_session()
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError

        result = dict()
        hospital_uid_from = kwargs.get('hospitalUidFrom', '')

        params = dict(firstName=patient.firstName,
                      lastName=patient.lastName,
                      patronymic=patient.patronymic,
                      document=document,
                      birthday=birthday,
                      sex=sex,
                      hospitalUidFrom=hospital_uid_from)
        try:
            result = proxy_client.get_patient_tickets(params)
        except Exception, e:
            print e
            logger.error(e, extra=logger_tags)
            return dict(status=False, message=u'Пациент не найден')
        else:
            if result.get('tickets', None):
                result['tickets'] = self.__prepare_tickets_info(hospital_uid,
                                                                lpu_info,
                                                                result['patient'],
                                                                result['tickets'])
                del result['patient']
        return result

    def __get_ticket_print(self, **kwargs):
        """
        Return generated pdf for ticket print
        !NOT USED
        """
        # TODO: выяснить используется ли pdf в принципе. В эл.регестратуре он никак не используется
        # TODO: pdf creator based on Flask templates and xhtml2pdf
        return ""

    def enqueue(self, **kwargs):
        """Запись на приём к врачу

        Args:
            person: { ФИО пациента (обязательный)
                'firstName'
                'lastName'
                'patronymic'
            }
            hospitalUid:
                uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            birthday: дата рождения пациента (необязательный)
            doctorUid: id врача, к которому производится запись (обязательный)
            omiPolicyNumber: номер полиса мед. страхования (необязательный)
            sex: пол (необязательный)
            timeslotStart: время записи на приём (обязательный)
            hospitalUidFrom: uid ЛПУ, с которого производится запись (необязательный), используется для записи между ЛПУ

        """
        hospital_uid = kwargs.get('hospitalUid', '')
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        birthday = kwargs.get('birthday')
        doctor_uid = kwargs.get('doctorUid')
        patient = kwargs.get('person')
        sex = kwargs.get('sex')
        omi_policy_number = kwargs.get('omiPolicyNumber')
        if omi_policy_number:
            omi_policy_number = omi_policy_number.strip()
        document_obj = kwargs.get('document')
        document = dict()
        if document_obj:
            if document_obj.client_id:
                document['client_id'] = str(document_obj.client_id)
            if document_obj.policy_type:
                document['policy_type'] = str(document_obj.policy_type)
            if document_obj.document_code:
                document['document_code'] = str(document_obj.document_code)
            if document_obj.series:
                document['serial'] = document_obj.series
            else:
                document['serial'] = ''
            if document_obj.number:
                document['number'] = document_obj.number

        timeslot_start = kwargs.get('timeslotStart', '')

        if hospital_uid and doctor_uid and patient:
            if len(hospital_uid) > 1:
                dw = DataWorker.provider('lpu')
                lpu_info = dw.get_by_id(hospital_uid[0])
                task_hospital = dict(auth_token=lpu_info.token, place_id=lpu_info.keyEPGU)
                proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
            else:
                shutdown_session()
                logger.error(exceptions.ValueError(), extra=logger_tags)
                raise exceptions.ValueError
        else:
            shutdown_session()
            logger.error(exceptions.ValueError(), extra=logger_tags)
            raise exceptions.ValueError

        result = dict()

        person_dw = DataWorker.provider('personal')
        doctor_info = person_dw.get_doctor(lpu_unit=hospital_uid, doctor_id=doctor_uid)

        service_type = doctor_info.speciality[0].epgu_service_type
        task_doctor = dict(location_id=getattr(doctor_info.key_epgu, 'keyEPGU', None),
                           epgu_service_type=getattr(service_type, 'keyEPGU', None))
        hospital_uid_from = kwargs.get('hospitalUidFrom', '')

        if not doctor_info:
            shutdown_session()
            logger.error(exceptions.LookupError(), extra=logger_tags)
            raise exceptions.LookupError

        person_fio = dict(firstName=patient.firstName,
                          lastName=patient.lastName,
                          patronymic=patient.patronymic)

        # Отправляет запрос на SOAP КС для записи пациента
        _enqueue = proxy_client.enqueue(
            serverId=lpu_info.key,
            person=person_fio,
            omiPolicyNumber=omi_policy_number,
            document=document,
            birthday=birthday,
            sex=sex,
            hospitalUid=hospital_uid[1],
            hospitalUidFrom=hospital_uid_from,
            speciality=doctor_info.speciality[0].name.lower(),
            doctorUid=doctor_uid,
            timeslotStart=timeslot_start
        )

        if _enqueue and _enqueue['result'] is True:

            ticket_uid = _enqueue.get('ticketUid').split('/')
            enqueue_id = self.__add_ticket(
                Error=_enqueue.get('error_code'),
                Data=json.dumps({
                    'ticketUID': _enqueue.get('ticketUid'),
                    'timeslotStart': timeslot_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'hospitalUid': kwargs.get('hospitalUid'),
                    'doctorUid': doctor_uid,
                }),
                patient_id=_enqueue.get('patient_id'),
                ticket_id=int(ticket_uid[0]),
            )

            result = {'result': _enqueue.get('result'),
                      #TODO: переработать систему уведомлений
                      'message': exception_by_code(_enqueue.get('message')),
                      'ticketUid': _enqueue.get('ticketUid')}

            # Call Task send_enqueue to epgu

            send_enqueue_task.delay(
                hospital=task_hospital,
                doctor=task_doctor,
                patient=dict(fio=person_fio, id=_enqueue.get('patient_id')),
                timeslot=timeslot_start,
                enqueue_id=enqueue_id,
                slot_unique_key=kwargs.get('epgu_slot_id'))
        else:
            enqueue_id = self.__add_ticket(
                Error=_enqueue.get('error_code'),
                Data=json.dumps({
                    'ticketUID': _enqueue.get('ticketUid'),
                    'timeslotStart': timeslot_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'hospitalUid': kwargs.get('hospitalUid'),
                    'doctorUid': doctor_uid,
                }),
            )

            result = {
                'result': _enqueue.get('result'),
                'message': exception_by_code(_enqueue.get('error_code')),
                'ticketUid': 'e' + str(enqueue_id)
            }
        shutdown_session()
        return result

    def __delete_epgu_slot(self, hospital, patient_id, ticket_id):
        if not hospital.token or not hospital.keyEPGU:
            return None
        # TODO: может возникнуть ситуация, когда patient_id и ticket_id совпадают для разных ЛПУ
        # TODO: тогда может не произвестись отмена записи на ГП, т.к. мы достанем не тот keyEPGU
        # TODO: решается учётом lpu_id
        enqueue_record = (self.session.query(Enqueue).
                          filter(and_(Enqueue.patient_id == int(patient_id), Enqueue.ticket_id == int(ticket_id))).
                          one())
        _hospital = dict(auth_token=hospital.token, place_id=hospital.keyEPGU)
        if enqueue_record:
            # epgu_dw = EPGUWorker()
            # epgu_dw.epgu_delete_slot(_hospital, enqueue_record.keyEPGU)

            # Call task delete slot in EPGU
            epgu_delete_slot_task.delay(_hospital, enqueue_record.keyEPGU)

    def __add_ticket(self, **kwargs):
        """Добавляет информацию о талончике в БД ИС"""
        try:
            enqueue = Enqueue(**kwargs)
            self.session.add(enqueue)
        except exceptions.ValueError, e:
            print e
            logger.error(e, extra=logger_tags)
            self.session.rollback()
        except exceptions.Exception, e:
            print e
            logger.error(e, extra=logger_tags)
            self.session.rollback()
        else:
            self.session.commit()
            return enqueue.id
        return None

    def update_enqueue(self, enqueue_id, data):
        """Обновляет информацию о талончике в БД ИС"""
        try:
            enqueue = self.session.query(Enqueue).get(enqueue_id)
            for k, v in data.items():
                if hasattr(enqueue, k):
                    setattr(enqueue, k, v)
        except exceptions.ValueError, e:
            print e
            logger.error(e, extra=logger_tags)
            self.session.rollback()
        except exceptions.Exception, e:
            print e
            logger.error(e, extra=logger_tags)
            self.session.rollback()
        else:
            self.session.commit()
            return enqueue.id
        return None

    def dequeue(self, **kwargs):
        """Отменяет запись на приём

        Args:
            hospitalUid:
                uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            ticketUid: Идентификатор ранее поданной заявки о записи на приём (обязательный)

        """
        hospital_uid = kwargs.get('hospitalUid', '')
        ticket_uid = kwargs.get('ticketUid', '')
        if hospital_uid:
            hospital_uid = hospital_uid.split('/')
        if len(hospital_uid) > 1:
            dw = DataWorker.provider('personal')
            lpu_info = dw.get_by_id(hospital_uid[0])
            proxy_client = Clients.provider(lpu_info.protocol, lpu_info.proxy.split(';')[0])
        else:
            shutdown_session()
            return dict()

        if ticket_uid:
            ticket_uid = ticket_uid.split('/')
        if len(hospital_uid) > 1:
            ticket_id = ticket_uid[0]
            patient_id = ticket_uid[1]
        else:
            shutdown_session()
            return dict()

        result = proxy_client.dequeue(server_id=lpu_info.key, patient_id=patient_id, ticket_id=ticket_id)
        if result and result['success']:
            self.__delete_epgu_slot(hospital=lpu_info, patient_id=patient_id, ticket_id=ticket_id)

        shutdown_session()
        return result

    def get_new_tickets(self, lpu_id):
        result = None
        lpu_dw = DataWorker.provider('lpu')
        lpu = lpu_dw.get_by_id(lpu_id)
        proxy_client = Clients.provider(lpu.protocol, lpu.proxy.split(';')[0])
        method = 'get_new_tickets'
        if hasattr(proxy_client, method) and callable(getattr(proxy_client, method)):
            result = proxy_client.get_new_tickets()
        return result


#INLINE EPGU TASKS
from is_celery.celery_init import celery


@celery.task(interval_start=5, interval_step=5)
def send_enqueue_task(hospital, doctor, patient, timeslot, enqueue_id, slot_unique_key):
    Task_Session = init_task_session()
    try:
        epgu_dw = DataWorker.provider('epgu', Task_Session())
        epgu_dw.send_enqueue(hospital, doctor, patient, timeslot, enqueue_id, slot_unique_key)
    except exceptions.Exception, e:
        logger.error(e, extra=logger_tags)
        print e
    finally:
        Task_Session.remove()


@celery.task(interval_start=5, interval_step=5)
def epgu_delete_slot_task(_hospital, enqueue_keyEPGU):
    Task_Session = init_task_session()
    try:
        epgu_dw = DataWorker.provider('epgu', Task_Session())
        epgu_dw.epgu_delete_slot(_hospital, enqueue_keyEPGU)
    except exceptions.Exception, e:
        logger.error(e, extra=logger_tags)
        print e
    finally:
        Task_Session.remove()