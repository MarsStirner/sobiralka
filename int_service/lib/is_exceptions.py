# -*- coding: utf-8 -*-
from exceptions import Exception, ValueError


#Define exceptions
class ISError(Exception):
    pass


class ISInvalidInputParametersError(ISError):
    pass


class IS_ConnectionError(ISError):
    message = u'Ошибка связи.'

    def __init__(self, host=None):
        if host:
            self.message += u' Хост: %s' % host


class IS_PatientNotRegistered(ISError):
    message = u'Пациент не зарегистрирован в выбранном ЛПУ'


class IS_FoundMultiplePatients(ISError):
    message = u'Найдено более одного пациента по указанным данным'


class IS_NoSuchPatientTypeId(ISError):
    message = u'Указанного типа идентификатора пациента не существует'


class IS_NoSuchPatientId(ISError):
    message = u'передали id пациента - а такой записи нет (или она удалена)'


class IS_DeadPatient(ISError):
    message = u'пациент отмечен как умерший'


class IS_FailedAgeOrSex(ISError):
    message = u'пациент не подходит по полу или возрасту'


class IS_NoActiveTickets(ISError):
    message = u'очереди (записи) у указанного врача на указанную дату нет'


class IS_TicketNotExists(ISError):
    message = u'в очереди нет приёма на это время'


class IS_PatientAlreadyEnqueue(ISError):
    message = u'пациент уже записан'


class IS_BusyTicket(ISError):
    message = u'талон уже занят'


class IS_PatientQueueNotFound(ISError):
    message = u'указанная запись на приём к врачу не найдена'


class IS_PatientHasNotAttachment(ISError):
    message = u'пациент не имеет прикрепления'


class IS_AttachmentHasNotService(ISError):
    message = u'прикрепление пациента не предусматривает обслуживание'


class IS_WorkWithSMOPatientsTerminated(ISError):
    message = u'работа с клиентами СМО приостановлена'


class IS_EnqueueDenied(ISError):
    message = u'Постановка в очередь запрещена'


class IS_NoTicketsAvailable(ISError):
    message = u'Нет свободных талончиков на заданное время (квота исчерпана)'


def exception_by_code(code):
    exc = {
        200: IS_PatientNotRegistered,
        201: IS_FoundMultiplePatients,
        202: IS_NoSuchPatientTypeId,
        210: IS_ConnectionError,
        302: IS_NoSuchPatientId,
        303: IS_DeadPatient,
        304: IS_FailedAgeOrSex,
        305: IS_NoActiveTickets,
        306: IS_TicketNotExists,
        307: IS_PatientAlreadyEnqueue,
        308: IS_BusyTicket,
        309: IS_PatientQueueNotFound,
        310: IS_PatientHasNotAttachment,
        311: IS_AttachmentHasNotService,
        312: IS_WorkWithSMOPatientsTerminated,
        400: IS_EnqueueDenied,
        401: IS_NoTicketsAvailable,
    }
    try:
        num_code = int(code.split()[0])
    except ValueError:
        return code
    else:
        return exc[num_code].message if num_code in exc else code