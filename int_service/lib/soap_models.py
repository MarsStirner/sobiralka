# coding: utf-8 -*-

from spyne.model.primitive import String, Unicode, Integer, Date, DateTime, Boolean
from spyne.model.complex import Array, ComplexModel
from spyne.model.enum import Enum
from spyne.model.binary import ByteArray

from settings import SOAP_NAMESPACE

# INFO MODELS
class HospitalAddress(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    id = Integer()
    uid = Unicode()
    name = Unicode()
    name.Annotations.doc=u'Наименование объекта (корпуса, отделения) ЛПУ, расположенных по данному адресу'
    address = Unicode()
    address.Annotations.doc=u'Почтовый адрес объекта'
    phone = String(doc=u'Телефон объекта')
    phone.Annotations.doc=u'Телефон объекта'
    route = Unicode()
    route.Annotations.doc = u'Информация о маршруте проезда'
    schedule = Unicode()
    schedule.Annotations.doc=u'Информация о расписании работы объекта, если оно отличается от общего расписания работы ЛПУ'

    def __init__(self, **kwargs):
        super(HospitalAddress, self).__init__(doc = u'Информация об адресе ЛПУ', **kwargs)


class ServicedDistrict(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    addressInfo = Unicode()
    addressInfo.Annotations.doc=u'Информация об адресе или  адресах, обслуживаемом данным врачом ЛПУ'
    doctorUid = String()
    doctorUid.Annotations.doc=u'Уникальный идентификатор врача в Реестре'
    doctor = Unicode()
    doctor.Annotations.doc=u'ФИО врача'
    speciality = Unicode()
    speciality.Annotations.doc=u'Специальность врача'

    def __init__(self, **kwargs):
        super(ServicedDistrict, self).__init__(doc=u'Информация об обслуживаемом участке', **kwargs)


class DetailedHospitalInfo(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    uid = Unicode()
    uid.Annotations.doc=u'Уникальный идентификатор ЛПУ'
    name = Unicode()
    name.Annotations.doc=u'Полное наименование ЛПУ'
    type = Unicode()
    type.Annotations.doc=u'Наименование типа (категории) ЛПУ'
    phone = String()
    phone.Annotations.doc=u'Номер телефона ЛПУ'
    email = Unicode()
    email.Annotations.doc=u'Адрес электронной почты ЛПУ'
    siteURL = String()
    siteURL.Annotations.doc=u'Адрес сайта ЛПУ'
    schedule = Unicode()
    schedule.Annotations.doc=(u'Информация о расписании работы объекта, '
                              u'если оно отличается от общего расписания работы ЛПУ')
    buildings = HospitalAddress.customize(max_occurs='unbounded', doc=u'Перечень адресов зданий, входящих в состав ЛПУ')
    servicedDistricts = ServicedDistrict.customize(max_occurs='unbounded')

    def __init__(self, **kwargs):
        super(DetailedHospitalInfo, self).__init__(doc = u'Подробная информация о ЛПУ', **kwargs)


class Hospital(ComplexModel):
    __namespace__ = SOAP_NAMESPACE


class GetHospitalInfoRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String.customize( nillable=True, minOccurs=0, doc=u'Один или несколько идентификаторов ЛПУ')

    def __init__(self):
        super(GetHospitalInfoRequest, self).__init__(doc=u'Параметры запроса для получения подробной информация о ЛПУ')


class GetHospitalInfoResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    info = DetailedHospitalInfo.customize(max_occurs='unbounded')

    def __init__(self):
        super(GetHospitalInfoResponse, self).__init__(doc=u'Подробная информация о запрошенных ЛПУ')


class SetHospitalInfoRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String()
    hospitalUid.Annotations.doc=u'Один идентификатор ЛПУ'
    keyEPGU = String()
    keyEPGU.Annotations.doc=u'идентификатор ЛПУ на ЕПГУ'

    def __init__(self):
        super(SetHospitalInfoRequest, self).__init__(doc=u'Параметры запроса для обновления информация о ЛПУ')


class DetailedOperationStatus(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    status = String()
    status.Annotations.doc=u'Статус операции'
    errMessage = String()
    errMessage.Annotations.doc=u'Сообщение об ошибке'


class SetDoctorInfoResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    info = DetailedOperationStatus()


class GetHospitalUidRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalCode = String()
    hospitalCode.Annotations.doc=u'Один или несколько идентификаторов ЛПУ'

    def __init__(self):
        super(GetHospitalUidRequest, self).__init__(
            doc=u'Параметры запроса для получения идентификатора ЛПУ по его ИНФИС коду'
        )


class GetHospitalUidResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String()
    hospitalUid.Annotations.doc=u'Идентификатор ЛПУ'

    def __init__(self):
        super(GetHospitalUidResponse, self).__init__(doc=u'Идентификатор ЛПУ')


class PersonName(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    firstName = Unicode
#    firstName.Annotations.doc=u'Имя'
    patronymic = Unicode
#    patronymic.Annotations.doc=u'Отчество'
    lastName = Unicode
#    lastName.Annotations.doc=u'Фамилия'

    def __init__(self, **kwargs):
        doc = kwargs.pop('doc', u'ФИО')
        super(PersonName, self).__init__(doc=doc, **kwargs)


class DoctorInfo(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    uid = Integer
#    uid.Annotations.doc=u'Уникальный идентификатор врача в Реестре'
    name = PersonName
    hospitalUid = String
#    hospitalUid.Annotations.doc=u'Уникальный идентификатор ЛПУ'
    speciality = Unicode
#    speciality.Annotations.doc=u'Наименование специальности'
    keyEPGU = String
#    keyEPGU.Annotations.doc=u'Ключ на ЕПГУ'

    def __init__(self, **kwargs):
        super(DoctorInfo, self).__init__(doc=u'Информация о враче', **kwargs)


class HospitalInfo(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    uid = String()
    uid.Annotations.doc=u'Уникальный идентификатор ЛПУ'
    name = Unicode()
    name.Annotations.doc=u'Наименование ЛПУ'
    phone = String()
    phone.Annotations.doc=u'Номер телефона ЛПУ'
    address = Unicode()
    address.Annotations.doc=u'Адрес ЛПУ'
    wsdlURL = String()
    wsdlURL.Annotations.doc=u'URL веб-сервиса МИС, предоставляющего возможность записи на приём'
    token = String()
    token.Annotations.doc=u'Токен ЛПУ'
    key = String()
    key.Annotations.doc=u'Key ЛПУ'

    def __init__(self, **kwargs):
        super(HospitalInfo, self).__init__(doc=u'Основная информация об ЛПУ', **kwargs)


class ServTypesInfo(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    id = String(doc=u'Уникальный идентификатор услуги в Реестре')
    servTypeName = Unicode(doc=u'Наименование услуги')
    speciality = Unicode(doc=u'Наименование специальности')
    keyEPGU = String(doc=u'ключ на EPGU')

    def __init__(self, **kwargs):
        super(ServTypesInfo, self).__init__(doc=u'Информация об услугах', **kwargs)


class NewEnqueue(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    id = String(doc=u'Уникальный идентификатор услуги в Реестре')
    LPUKey = String(doc=u'Key LPU')
    EPGUKey = String(doc=u'ключ на EPGU')
    Status = Unicode(doc=u'Статус')
    data = Unicode(doc=u'Наименование услуги')

    def __init__(self, **kwargs):
        super(NewEnqueue, self).__init__(doc=u'Запись пациента', **kwargs)


class SpecialtyInfo(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    speciality = Unicode(doc=u'Наименований специальности')
    ticketsPerMonths = String(doc=u'Количество талончиков на месяц')
    ticketsAvailable = String(doc=u'Количество доступных талончиков')
    nameEPGU = String(doc=u'на EPGU')

    def __init__(self, **kwargs):
        super(SpecialtyInfo, self).__init__(doc=u'Наименований специальности', **kwargs)


# LIST MODELS
class BuildingNumber(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    building = Unicode
#    building.Annotations.doc=u'Указание на литеру, корпус, строение'
    number = Integer
#    number.Annotations.doc=u'Номер дома'

    def __init__(self, **kwargs):
        super(BuildingNumber, self).__init__(doc=u'Номер дома', **kwargs)


class ParsedAddress(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    block = String
#    block.Annotations.doc=u'Номер квартала (для муниципальных образований, ' \
#                          u'в которых адресация зданий производится с помощью кварталов, а не улиц)'
    flat = Integer
#    flat.Annotations.doc=u'Номер квартиры'
    house = BuildingNumber
    kladrCode = String
#    kladrCode.Annotations.doc=u'Идентификатор по классификатору КЛАДР. Для муниципальных образований, ' \
#                              u'использующих улицы при адресации зданий -- идентификатор улицы, ' \
#                              u'для муниципальных образований, ' \
#                              u'использующих для тех же целей номера кварталов ' \
#                              u'- идентификатор муниципального образования'

    def __init__(self, **kwargs):
        super(ParsedAddress, self).__init__(doc=u'Структурированная информация об адресе', **kwargs)


class Address(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    rawAddress = Unicode
#    rawAddress.Annotations.doc=u'Адрес объекта, записанный в виде строки'
    parsedAddress = ParsedAddress

    def __init__(self, **kwargs):
        super(Address, self).__init__(doc=u'Информация об адресе', **kwargs)


class SearchScope(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String
#    hospitalUid.Annotations.doc=u'Один или несколько идентификаторов ЛПУ'
    ocatoCode = String
#    ocatoCode.Annotations.doc=u'Код муниципального образования по классификатору ОКАТО'
    address = Address

    def __init__(self, **kwargs):
        super(SearchScope, self).__init__(doc=u'Область поиска (территориальные критерии)', **kwargs)


class ListNewEnqueueRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String(doc=u'Уникальный идентификатор ЛПУ, для которого надо вернуть список новых записей')
    EPGUKey = String(doc=u'Key EPGU')

    def __init__(self):
        super(ListNewEnqueueRequest, self).__init__(doc=u'Критерии для получения списка новых записей')


class ListNewEnqueueResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    Enqueue = NewEnqueue.customize(max_occurs='unbounded')

    def __init__(self):
        super(ListNewEnqueueResponse, self).__init__(doc=u'Результаты поиска услуги по заданным критериям')


class ListServTypesInfoRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String(
        doc=u'Перечень уникальных идентификаторов ЛПУ, для которых надо вернуть перечень специальностей'
    )

    def __init__(self):
        super(ListServTypesInfoRequest, self).__init__(doc=u'Критерии для получения списка услуг')


class ListServTypesInfoResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    ServTypes = ServTypesInfo.customize(
        max_occurs='unbounded', doc=u'Перечень объектов, содержащих информацию о найденных услугах'
    )

    def __init__(self):
        super(ListServTypesInfoResponse, self).__init__(doc=u'Результаты поиска услуги по заданным критериям')


class ListDoctorsRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    lastName = Unicode
#    lastName.Annotations.doc=u'Фамилия врача'
    speciality = Unicode
#    speciality.Annotations.doc=u'Наименование специальности'
    searchScope = SearchScope

    def __init__(self):
        super(ListDoctorsRequest, self).__init__(doc=u'Один или несколько критериев поиска (получения списка) врачей')


class ListDoctorsResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    doctors = DoctorInfo.customize(
        nillable=True, minOccurs=0,
        max_occurs='unbounded', doc=u'Перечень объектов, содержащих информацию о найденных врачах'
    )
    hospitals = HospitalInfo.customize(
        max_occurs='unbounded', doc=u'Перечень связанных ЛПУ с краткой информацией. '
                                    u'Перечень может быть пустым только в том случае, если пуст перечень найденных врачей.'
    )
    addressVariants = Address.customize(
        max_occurs='unbounded',
        doc=u'Возможные варианты адреса, предлагаемые Реестром пользователю для уточнения. ' \
            u'Список генерируется, если запрос содержал критерий поиска "по адресу", ' \
            u'структурированная информация отсутствовала, ' \
            u'а при разборе адреса на стороне Реестра была выявлена неоднозначность ' \
            u'в трактовке входных данных.'
    )

    def __init__(self):
        super(ListDoctorsResponse, self).__init__(doc=u'Результаты поиска врача по заданным критериям')


class ListSpecialitiesRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String(
        doc=u'Перечень уникальных идентификаторов ЛПУ, для которых надо вернуть перечень специальностей'
    )
    hospitalUidFrom = String(doc=u'Идентификатор отправителя')

    def __init__(self):
        super(ListSpecialitiesRequest, self).__init__(doc=u'Критерии для получения списка специальностей')


class ListSpecialitiesResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    speciality = SpecialtyInfo.customize(max_occurs='unbounded', doc=u'Перечень найденных специальностей')

    def __init__(self):
        super(ListSpecialitiesResponse, self).__init__(doc=u'Результаты поиска специальностей по заданным критериям')


class ListHospitalsRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    speciality = Unicode
#    speciality.Annotations.doc=u'Наименование специальности'
    ocatoCode = String
#    ocatoCode.Annotations.doc=u'Код муниципального образования по классификатору ОКАТО'
    hospitalUid = String
#    hospitalUid.Annotations.doc=u'Перечень уникальных идентификаторов ЛПУ'
    searchScope = SearchScope

    def __init__(self):
        super(ListHospitalsRequest, self).__init__(doc=u'Критерии для получения списка ЛПУ')


class ListHospitalsResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitals = HospitalInfo.customize(max_occurs='unbounded', doc=u'Перечень найденных ЛПУ')
    addressVariants = Address.customize(max_occurs='unbounded',
        doc=u'Возможные варианты адреса, предлагаемые Реестром пользователю для уточнения. '
            u'Список генерируется, если запрос содержал критерий поиска "по адресу", '
            u'структурированная информация отсутствовала, '
            u'а при разборе адреса на стороне Реестра была выявлена неоднозначность в трактовке входных данных.')

    def __init__(self):
        super(ListHospitalsResponse, self).__init__(doc=u'Результаты поиска ЛПУ по заданным критериям')


# SCHEDULE MODELS
class GetScheduleInfoRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String(doc=u'Уникальный идентификатор ЛПУ')
    speciality = Unicode(doc=u'Специальность врача')
    doctorUid = String(doc=u'Уникальный идентификатор врача')
    startDate = Date(doc=u'Начало интересующего периода. Если не указан, принимается равным текущей дате')
    endDate = Date(
        doc=u'Окончание интересующего периода. '
            u'Если не указано, то интерпретируется в зависимости от значения параметра startDate: '
            u'если startDate находится в прошлом, то endDate принимается равным сегодняшней дате, '
            u'в противном случае его значение определяется настройками МИС и временем, '
            u'на которое планируется расписание.'
    )
    hospitalUidFrom = String(doc=u'Идентификатор отправителя')

    def __init__(self):
        super(GetScheduleInfoRequest, self).__init__(doc=u'Получение обобщённой информации о расписании врача')


Timeslot_Statuses = Enum(
    "free",
    "locked",
    "unavailable",
    type_name="Statuses"
)

class TimeslotStatus(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    timeslotStatus = Timeslot_Statuses

    def __init__(self, **kwargs):
        super(TimeslotStatus, self).__init__(doc=u'Состояние интервала времени в расписании', **kwargs)


class Timeslot(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    start = DateTime
#    start.Annotations.doc = u'Начало интервала'
    finish = DateTime
#    finish.Annotations.doc = u'Окончание интервала'
#    status = TimeslotStatus
    status = String
    office = String
#    office.Annotations.doc = u'Кабинет'
    patientId = Integer
#    patientId.Annotations.doc = u'Идентификатор записанного пациента'
    patientInfo = Unicode
#    patientInfo.Annotations.doc = u'ФИО записанного пациента'

    def __init__(self):
        super(Timeslot, self).__init__(doc=u'Интервал в расписании врача')


class GetScheduleInfoResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    timeslots = Timeslot.customize(max_occurs='unbounded', doc=u'Расписание на отдельные дни в заданном интервале')

    def __init__(self):
        super(GetScheduleInfoResponse, self).__init__(doc=u'Информация о расписании врача')


SessionStatuses = Enum(
    "unsupported",
    "busy",
    "available",
    "unavailable",
    type_name="SessionStatuses"
)

class SessionType(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    sessionStatus = SessionStatuses()

    def __init__(self, **kwargs):
        super(SessionType, self).__init__(doc=u'Статус группы интервалов в расписании врача', **kwargs)


class Session(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    sessionStart = DateTime(doc=u'Начало смены')
    sessionEnd = DateTime(doc=u'Окончание смены')
    sessionType = SessionType()
    timeslots = Timeslot.customize(
        max_occurs='unbounded', doc=u'Информация об отдельных элементах расписания (тайм-слотах)'
    )
    comments = Unicode(doc=u'Дополнительная информация о месте приёма или о замещениях')

    def __init__(self):
        super(Session, self).__init__(doc=u'Группа интервалов (смена) в расписании врача')


Ticket_Statuses = Enum(
    'accepted',
    'unconfirmed',
    'processing',
    'rejected',
    'forbidden',
    'canceledByHospital',
    'canceled',
    'rescheduled',
    'substituted',
    type_name='SessionStatuses',
)

class TicketStatus(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    ticketStatus = Ticket_Statuses()

    def __init__(self, **kwargs):
        super(TicketStatus, self).__init__(doc=u'Состояние заявки на приём у врача', **kwargs)


class EnqueueRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    person = PersonName
#    person.Annotations.doc=u'ФИО пациента (пользователя)'
    omiPolicyNumber = Unicode
#    omiPolicyNumber.Annotations.doc=u'Номер и серия полиса ОМС пациента (пользователя)'
    birthday = Date
#    birthday.Annotations.doc=u'Дата рождения пациента (пользователя)'
    sex = Integer
    #    sex.Annotations.doc=u'Пол пациента (пользователя)'
    hospitalUid = Unicode
#    hospitalUid.Annotations.doc=u'Уникальный идентификатор ЛПУ'
    speciality = Unicode
#    speciality.Annotations.doc=u'Специальность врача'
    doctorUid = Unicode
#    doctorUid.Annotations.doc=u'Уникальный идентификатор врача'
    timeslotStart = DateTime
#    timeslotStart.Annotations.doc=u'Желаемое время начала приёма'
    hospitalUidFrom = String
#    hospitalUidFrom.Annotations.doc=u'Уникальный идентификатор ЛПУ отправителя'

    def __init__(self):
        super(EnqueueRequest, self).__init__(doc=u'Данные запроса о записи на приём')


class EnqueueResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    result = Boolean(doc=u'Результат запроса о записи на приём')
    message = String(doc=u'Сообщение об ошибке')
    ticketUid = String(doc=u'Уникальный для МИС данного ЛПУ идентификатор принятой заявки')
    printableDocument = String(doc=u'Данныее электронного документа с печатной формой заявки на приём (талоном)')

    def __init__(self):
        super(EnqueueResponse, self).__init__(doc=u'Данные запроса о записи на приём')


class CancelRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String(doc=u'Уникальный идентификатор ЛПУ')
    ticketUid = String(doc=u'Идентификатор ранее поданной заявки о записи на приём')

    def __init__(self):
        super(CancelRequest, self).__init__(doc=u'Данные запроса об отмене записи на приём')


class CancelResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    success = Boolean(doc=u'Признак успешности выполнения операции')
    comment = Unicode(doc=u'Дополнительная информация о результатах выполнения операции')

    def __init__(self):
        super(CancelResponse, self).__init__(doc=u'Результат запроса об отмене записи на приём')


class DetailedOperationStatus(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    status = String(doc=u'Статус операции')
    errMessage = Unicode(doc=u'Сообщение об ошибке')

    def __init__(self):
        super(DetailedOperationStatus, self).__init__(doc=u'Подробная информация о статусе')


class SetTicketReadStatusRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    ticketID = String(doc=u'Один идентификатор записи')
    EPGUKey = String(doc=u'EPGU Key')
    LPUKey = String(doc=u'LPU Key')
    value = Unicode(doc=u'значение')

    def __init__(self):
        super(SetTicketReadStatusRequest, self).__init__(doc=u'Параметры запроса для обновления  информация о записи')


class SetTicketReadStatusResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    info = DetailedOperationStatus

    def __init__(self):
        super(SetTicketReadStatusResponse, self).__init__(doc=u'Запрос о текущем статусе заявки на приём')


class PrintableDocument(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    printableVersionTitle = Unicode(doc=u'Название элетронного документа, прилагаемого к данным о статусе заявления')
    printableVersion = ByteArray(doc=u'Содержание элетронного документа, прилагаемого к данным о статусе заявления')
    printableVersionMimeType = String(
        doc=u'Тип содержания (mime-type) элетронного документа, прилагаемого к данным о статусе заявления.'
    )

    def __init__(self, **kwargs):
        super(PrintableDocument, self).__init__(
            doc=u'Данные электронного документа, который может быть приложен к информации о статусе заявки',
            **kwargs
        )


class TicketInfo(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    id = String(doc=u'Уникальный для ИС идентификатор заявки')
    ticketUid = String(doc=u'Уникальный для МИС ЛПУ идентификатор заявки')
    hospitalUid = String(doc=u'Уникальный идентификатор ЛПУ')
    doctorUid = String(doc=u'Уникальный идентификатор врача')
    doctor = PersonName(doc=u'ФИО врача')
    person = PersonName(doc=u'ФИО записавшегося')
    status = TicketStatus()
    timeslotStart = DateTime(doc=u'Начало приёма у врача, соответствующее данной заявке')
    location = Unicode(doc=u'Информация о месте приёма (копрус, этаж, кабинет и т.п.)')
    comment = Unicode(doc=u'Дополнительные указания и информация')
    printableDocument = PrintableDocument()

    def __init__(self):
        super(TicketInfo, self).__init__( doc=u'Данные о текущем статусе заявки на приём')


class GetTicketStatusRequest(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    hospitalUid = String(doc=u'Уникальный идентификатор ЛПУ')
    ticketUid = String(doc=u'Уникальный для МИС соответствующего ЛПУ идентификатор ранее поданной заявки на приём')
    lastUid = String(doc=u'Последний обработанный тикет')

    def __init__(self):
        super(GetTicketStatusRequest, self).__init__(doc=u'Данные запроса о текущем статусе заявки на приём')


class GetTicketStatusResponse(ComplexModel):
    __namespace__ = SOAP_NAMESPACE

    ticketsInfo = TicketInfo.customize(max_occurs='unbounded', doc=u'Данные о состоянии запрошенных заявок')

    def __init__(self):
        super(GetTicketStatusResponse, self).__init__( doc=u'Ответ на запрос о текущем статусе заявки на приём')


