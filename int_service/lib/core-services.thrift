namespace java ru.korus.tmis.communication.thriftgen
//Namespace=package name for java

typedef i64 timestamp
typedef i16 short

/////////////////////////////////////////////////////////////////////
//Enums
/////////////////////////////////////////////////////////////////////

/**
 * QuotingType
 * Перечисление типов квотирования
 */
enum QuotingType{
    // из регистратуры
    FROM_REGISTRY = 1,
    //повторная запись врачем
    SECOND_VISIT = 2,
    // меж-кабинетная запись
    BETWEEN_CABINET = 3,
    // другое ЛПУ
    FROM_OTHER_LPU = 4,
    //с портала
    FROM_PORTAL = 5
}

/**
 * CouponStatus
 * Перечисление статусов талончика на прием к врачу
 */
enum CouponStatus{
	// новый талончик
	NEW = 1;
	// отмена старого талончика
	CANCELLED = 2;
}

/////////////////////////////////////////////////////////////////////
//Exceptions
/////////////////////////////////////////////////////////////////////

exception NotFoundException {
 1: string error_msg;
}
exception SQLException {
  1: i32 error_code;
  2: string error_msg;
}

exception InvalidPersonalInfoException{
	1:string message;
	2:i32 code;
}

exception InvalidDocumentException{
	1:string message;
	2:i32 code;
}

exception AnotherPolicyException{
	1:string message;
	2:i32 code;
	3:i32 patientId;
}

exception NotUniqueException{
	1:string message;
	2:i32 code;
}

exception PolicyTypeNotFoundException{
    1:string message;
    2:i32 code;
}

exception ReasonOfAbsenceException{
    1:string name;
    2:string code;
}

/////////////////////////////////////////////////////////////////////
//Type definitions for return structures
/////////////////////////////////////////////////////////////////////

/**
 * Organization 
 * Структура с данными об организации
 * @param fullName				1) Полное наименование организации
 * @param shortName				2) Краткое наименование организации
 * @param address				3) Строковое представление адреса организации
 * @param infisCode				4) Инфис-код организации 
 */
struct Organization{
1:required string fullName;
2:optional string shortName;
3:optional string address;
4:required string infisCode;
}

/**
 * OrgStructure 
 * Структура с данными о подразделении
 * @param id					1) Внутренний идентификатор подразделения
 * @param parent_id				2) Внутренний идентификатор вышестоящего подразделения, или 0 если вышестоящего отделеия не существует
 * @param code					3) Код подразделения
 * @param name					4) Название подразделения
 * @param address				5) Адрес подразделения
 * @param sexFilter				6) Половой фильтр
 * @param ageFilter				7) Возрастной фильтр
 * @param availableForExternal  8) Признак досутпности подразделения для внешних подсистем
 */
struct OrgStructure{
1:required i32 id;
2:optional i32 parent_id=0;
3:required string code;
4:required string name="";
5:optional string address="";
6:optional string sexFilter="";
7:optional string ageFilter="";
8:optional bool availableForExternal;
}

/**
 * Person
 * Структура с данными о мед. работнике
 * @param id					1) Внутренний идентификатор работника	
 * @param code					2) Код работника
 * @param orgStructureId		3) Идентификатор подразделения к которому работник приписан
 * @param lastName				4) Фамилия
 * @param firstName				5) Имя
 * @param patrName				6) Отчество
 * @param office				7) Офис, который указан в таблице персонала
 * @param speciality			8) Наименование специальности
 * @param specialityOKSOCode    9) ОКСО-код специальности
 * @param specialityRegionalCode 10) Региональный код специальности
 * @param post					11) Наименование должности
 * @param sexFilter				12) Пол работника
 * @param snils                 13) СНИЛС врача
 */
struct Person{
1:required i32 id;
2:required string code;
3:optional i32 orgStructureId;
4:optional string lastName;
5:optional string firstName;
6:optional string patrName;
7:optional string office;
8:optional string speciality;
9:optional string specialityOKSOCode;
10:optional string specialityRegionalCode;
11:optional string post;
12:optional string sexFilter;
13:optional string snils;
}

//@deprecated
struct Ticket{
1:optional timestamp time;
2:optional i32 free;
3:optional i32 available;
4:optional i32 patientId;
5:optional string patientInfo;
}

struct TicketsAvailability{
1:required i32 total;
2:required i32 free;
3:required i32 available;
}

struct ExtendedTicketsAvailability{
1:required i32 personId;
2:optional timestamp date;
3:required TicketsAvailability ticketsInfo;
}

//@deprecated
struct Amb{
1:optional timestamp begTime;
2:optional timestamp endTime;
3:optional string office;
4:optional i32 plan;
5:optional list<Ticket> tickets;
6:optional i32 available;
}

/**
 * PatientStatus
 * Структура с данными о  результате поиска \ добавления пациента
 * @param success				1) Статус поиска\добавления пациента (true - найдено\добавлено)
 * @param message				2) Строковое описание причины неудачи
 * @param patientId				3) Идентификатор найденного\добавленого пациента 
 */
struct PatientStatus{
1:required bool success;
2:optional string message;
3:optional i32 patientId;
}

/**
 * Patient
 * Структура с данными о пациенте
 * @param id					1) Внутренний идентификатор пациента
 * @param lastName				2) Фамилия
 * @param firstName				3) Имя
 * @param patrName				4) Отчество
 * @param birthDate				5) Дата рождения
 * @param sex					6) Пол (1-М, 2-Ж)
 */
struct Patient{
1:required i32 id;
2:optional string lastName;
3:optional string firstName;
4:optional string patrName;
5:optional timestamp birthDate;
6:optional i32 sex;
}

/**
 * OrgStructuresProperties
 * НЕ РЕАЛИЗОВАНО
 */
struct OrgStructuresProperties{
1:required i32 orgStructureId;
2:optional bool attached;
3:optional bool matchRegAddress;
4:optional bool matchLocAddress;
}

/**
 * EnqueuePatientStatus
 * Статус записи пациента к врачу
 * @param success				1) Флажок успешности записи к врачу
 * @param message				2) Сообщение
 * @param index					3) Индекс ячейки записи
 * @param queueId				4) Идентификатор новой записи
 */
struct EnqueuePatientStatus{
1:required bool success;
2:optional string message;
3:optional i32 index;
4:optional i32 queueId;
}

/**
 * Queue
 * Структура с данными о записях пациента к врачам
 * @param dateTime				1) Дата+время начала талончика
 * @param index					2) Индекс ячейки записи
 * @param personId				3) Идентификатор врача
 * @param note					4) Примечание
 * @param queueId				5) Идентификатор Action-а записи к врачу
 * @param enqueuePersonId		6) Идентификатор врача, который записал пациента
 * @param enqueueDateTime		7) Дата+время создания записи
 */
struct Queue{
1:optional timestamp dateTime;
2:optional i32 index;
3:optional i32 personId;
4:optional string note;
5:optional i32 queueId;
6:optional i32 enqueuePersonId;
7:optional timestamp enqueueDateTime;
}

/**
 * DequeuePatientStatus
 * Структура со статусом отмены записи пациента к врачу
 * @param success				1) Статус отмены записи пациента к врачу
 * @param message				2) Сообшение
 */
struct DequeuePatientStatus{
1:required bool success;
2:optional string message;
}

/**
 * Speciality
 * Структура с данными о специальностях врачей, на которые доступна внешняя запись
 * @param id 					1) Внутренний идентификатор специальности
 * @param ticketsPerMonths		2) Количество выделяемых талончиков в месяц
 * @param ticketsAvailable		3) Количество доступных талончиков (остатки)
 * @param speciality			4) Строковое название специальности
 */
struct Speciality{
1:required i32 id;
2:optional i32 ticketsPerMonths;
3:optional i32 ticketsAvailable;
4:optional string speciality;
}

/**
 * Address
 * Структура с данными об адресах, которые обслуживаются подразделением
 * @param orgStructureId		1) Внутренний идентификатор подразделения, к которому приписан этот адрес
 * @param pointKLADR			2) Соответствующий адресу КЛАДР-код
 * @param streetKLADR 			3) Соответствующий КЛАДР-код улицы
 * @param number				4) Номер дома\строения
 * @param corpus				5) Номер корпуса
 * @param firstFlat				6) Начало диапозона обслуживаемых квартир
 * @param lastFlat				7) Конец диапозона обслуживаемых квартир 
 */
struct Address{
1:required i32 orgStructureId;
2:required string pointKLADR;
3:required string streetKLADR;
4:optional string number;
5:optional string corpus;
6:optional i32 firstFlat;
7:optional i32 lastFlat;
}

/**
 * Contact
 * Структура с контактными данными пациента
 * @param type					1) Тип контакта
 * @param code					2) Код типа контакта
 * @param contact				3) Контактная информация
 * @param note					4) Примечание
 */
struct Contact{
1:optional string type;
2:optional string code;
3:optional string contact;
4:optional string note;
}

/**
 * QueueCoupon
 * Структура с данными для поллинга новых записей к врачу (чтобы учесть сделанные не через КС)
 * @param uuid                  1)Уникальный идентификатор талончика (отмененные талончики будут иметь тот-же идентификатор)
 * @param status                2)Статус талончика (Новый\Отменен)
 * @param personId              3)Ид врача
 * @param patient               4)Структура с данными пациента - владельца талончика
 * @param begDateTime           5)Дата+время начала талончика
 * @param endDateTime           5)Дата+время окончания талончика
 * @param office                6)Офис в котором будет принимать врач
 */
struct QueueCoupon{
1:required string uuid;
2:required CouponStatus status;
3:required i32 personId;
4:required Patient patient;
5:required timestamp begDateTime;
6:required timestamp endDateTime;
7:optional string office;
}

/**
 * TTicket
 * Структура с данными о талончике на прием к врачу
 * @param begTime           	1)Время начала талончика
 * @param endTime           	2)Время конца талончика
 * @param free              	3)признак, указывающий занят ли этот талончик каким-либо пациентом
 * @param available         	4)признак, указывающий доступен ли этот талончик для записи
 * @param patientId         	5) OPTIONAL: Идентификатор пациента, который занял этот талончик
 * @param patientInfo       	6) OPTIONAL: ФИО пациента, который занял этот талончик
 * @param timeIndex         	7) OPTIONAL: Индекс ячейки времени в расписании врача, на который ссылается этот талончик
 * @param date              	8) OPTIONAL: Дата приема врача. Будет выставляться для метода getFirstFreeTicket
 * @param office            	9) OPTIONAL: Офис, в котором будет происходить прием врача. Будет выставляться для метода getFirstFreeTicket
 */
struct TTicket{
1:required timestamp begTime;
2:required timestamp endTime;
3:required bool free;
4:required bool available;
5:optional i32 patientId;
6:optional string patientInfo;
7:optional i32 timeIndex;
8:optional timestamp date;
9:optional string office;
}

/**
 * Schedule
 * Структура с данными для расписания врача
 * @param begTime       		1) Время начала приема врача
 * @param endTime       		2) Время окончания приема врача
 * @param date          		3) Дата приема врача
 * @param office        		4) Офис в котором будет происходить прием
 * @param plan          		5) План приема (количество ячеек времени в которые врач будет принимать пациентов)
 * @param tickets       		6) Список талончиков на прием
 * @param available     		7) Признак доступности записи на этот прием (в целом)
 */
struct Schedule{
 1:required timestamp begTime;
 2:required timestamp endTime;
 3:required timestamp date;
 4:optional string office;
 5:optional i32 plan;
 6:optional list<TTicket> tickets;
 7:required bool available;
}

/**
 * PersonSchedule
 * Структура с данными о расписаниях врача за интервал
 * @param schedules             1) Расписания врача: map<timestamp, Schedule> - карта вида <[Дата приема], [Расписание на эту дату]>,
 *                                      в случае отсутствия расписания на указанную дату набор ключ-значение опускается
 * @param personAbsences        2) Список причин отсутствия врача
 */
struct PersonSchedule{
    1:required map<timestamp, Schedule> schedules;
    2:optional map<timestamp, ReasonOfAbsenceException> personAbsences;
}

/////////////////////////////////////////////////////////////////////
//Type definitions for input params
/////////////////////////////////////////////////////////////////////

/**
 * Policy
 * Структура с данными о полисе
 * @param serial            1)Серия полиса
 * @param number            2)Номер полиса
 * @param typeCode          3)Код типа полиса
 * @param insurerInfisCode  4)Инфис-код страховой организации
 */
struct Policy{
1:optional string serial;
2:required string number;
3:required string typeCode;
4:optional string insurerInfisCode;
}

struct FindOrgStructureByAddressParameters{
1:required string pointKLADR;
2:optional string streetKLADR="";
3:optional string number="";
4:optional string corpus="";
5:optional i32 flat=0;
}

struct GetTicketsAvailabilityParameters{
1:required i32 orgStructureId;
2:optional bool recursive;
3:optional string specialityNotation;
4:optional string speciality;
5:required i32 personId;
6:optional timestamp begDate;
7:optional timestamp endDate;
}

struct GetTimeWorkAndStatusParameters{
1:optional string hospitalUidFrom;
2:required i32 personId;
3:optional timestamp date;
}

/**
 * AddPatientParameters 	
 * Структура для создания нового пациента
 * @param lastName				1) Фамилия пациента
 * @param firstName				2) Имя пациента
 * @param patrName				3) Отчество пациента
 * @param birthDate				4) Дата рождения пациента
 * @param sex					5) Пол пациента
 * @param documentSerial		6) Серия документа
 * @param documentNumber		7) Номер документа
 * @param documentTypeCode		8) Код типа документа
 * @param policySerial			9) Серия полиса
 * @param policyNumber			10) Номер полиса
 * @param policyTypeCode		11) Код типа полиса
 * @param policyInsurerInfisCode	12)Инфис код страховой, полис которой представлен выше
 */ 
struct AddPatientParameters{
1:optional string lastName;
2:optional string firstName;
3:optional string patrName;
4:optional timestamp birthDate;
5:optional i32 sex;
6:optional string documentSerial;
7:optional string documentNumber;
8:optional string documentTypeCode;
9:optional string policySerial;
10:optional string policyNumber;
11:optional string policyTypeCode;
12:optional string policyInsurerInfisCode;
}

struct EnqueuePatientParameters{
1:required i32 patientId;
2:required i32 personId;
3:optional timestamp dateTime;
4:optional string note;
5:optional string hospitalUidFrom;
}

struct FindPatientParameters{
1:required string lastName;
2:required string firstName;
3:required string patrName;
4:required timestamp birthDate;
5:required i32 sex;
6:optional string identifierType;
7:optional string identifier;
8:required map<string, string> document;
}

struct FindMultiplePatientsParameters{
1:optional string lastName;
2:optional string firstName;
3:optional string patrName;
4:optional timestamp birthDate;
5:optional i32 sex;
6:optional string identifierType;
7:optional string identifier;
8:optional map<string, string> document;
}

/**
 * ChangePolicyParameters
 * Структура с данными для изменения/добавления полиса указанного клиента
 * @param patientId         1)Идентификатор пациента, которому нужно добавить/изменить полис
 * @param policy            2)Структура с данными для нового полиса
 */
struct ChangePolicyParameters{
1:required i32 patientId;
2:required Policy policy;
}

/**
 * FindPatientByPolicyAndDocumentParameters 	
 * Структура с данными для поиска пациента по ФИО, полису и документу
 * @param lastName				1)Фамилия пациента
 * @param firstName				2)Имя пациента
 * @param patrName				3)Отчество пациента
 * @param sex					4)Пол пациента
 * @param birthDate				5)Дата рождения пациента
 * @param documentSerial		6)Серия документа
 * @param documentNumber		7)Номер документа
 * @param documentTypeCode		8)Код типа документа
 * @param policySerial			9)Серия полиса
 * @param policyNumber			10)Номер полиса
 * @param policyTypeCode		11)Код типа полиса
 * @param policyInsurerInfisCode	12)Инфис код страховой, полис которой представлен выше
 */
struct FindPatientByPolicyAndDocumentParameters{
1:required string lastName;
2:required string firstName;
3:required string patrName;
4:required short sex;
5:required timestamp birthDate;
6:required string documentSerial;
7:required string documentNumber;
8:required string documentTypeCode;
9:optional string policySerial;
10:required string policyNumber;
11:required string policyTypeCode;
12:optional string policyInsurerInfisCode;
}

/**
 * Структура с данными для получения расписания пачкой и поиска превого свободного талончика
 * @param personId                  1)Идетификатор врача
 * @param beginDateTime             2)Время с которого начинается поиск свободных талончиков
 * @param endDateTime               3)Время до которого происходит поиск свободных талончиков
 (если не установлено - то плюс месяц к beginDateTime)
 * @param hospitalUidFrom           4)Идентификатор ЛПУ из которого производится запись
 * @param quotingType               5)Тип квотирования
 */
struct ScheduleParameters{
1:required i32 personId;
2:required timestamp beginDateTime;
3:optional timestamp endDateTime;
4:optional string hospitalUidFrom;
5:optional QuotingType quotingType;
}

/////////////////////////////////////////////////////////////////////
//Service 
/////////////////////////////////////////////////////////////////////

service Communications{

/////////////////////////////////////////////////////////////////////
//Methods 
/////////////////////////////////////////////////////////////////////

/**
 * получение информации об организации(ЛПУ) по ее инфис-коду
 * @param infisCode                     1)Инфис-код организации
 * @return                              Структуа с информацией об организации
 * @throws NotFoundException             когда в БД ЛПУ нету организации с таким инфис-кодом
 */
Organization getOrganisationInfo(1:string infisCode)
    throws (1:NotFoundException exc);

/**
 * Получение списка подразделений, входящих в заданное подразделение
 * @param parent_id                     1) идентификатор подразделения, для которого нужно найти дочернии подразделения
 * @param recursive                     2) Флаг рекурсии (выбрать также подразделения, входяшие во все дочерние подразделения)
 * @param infisCode                     3) Инфис-код
 * @return                              Список структур, содержащих информацию о дочерних подразделениях
 * @throws NotFoundException             когда не было найдено ни одного подразделения, удовлетворяющего заданным параметрам
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<OrgStructure> getOrgStructures(1:i32 parent_id, 2:bool recursive, 3:string infisCode)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Получение списка всех подразделений, относящихся к запрошенному ЛПУ
 * @param parent_id                     1) идентификатор подразделения, для которого нужно найти дочернии подразделения
 * @param recursive                     2) Флаг рекурсии (выбрать также подразделения, входяшие во все дочерние подразделения)
 * @param infisCode                     3) Инфис-код
 * @return                              Список структур, содержащих информацию о дочерних подразделениях
 * @throws NotFoundException             когда не было найдено ни одного подразделения, удовлетворяющего заданным параметрам
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<OrgStructure> getAllOrgStructures(1:i32 parent_id, 2:bool recursive, 3:string infisCode) throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Получение обслуживаемых адресов запрошенного подразделения
 * @param orgStructureId                1) идетификатор подразделения, для которого требуется найти обслуживаемые им адреса
 * @param recursive                     2) Флаг рекурсии (выбрать также подразделения, входяшие во все дочерние подразделения)
 * @param infisCode                     3) Инфис-код
 * @return                              Список структур, содержащих информацию об адресах запрошенных подразделений
 * @throws NotFoundException             когда не было найдено ни одного адреса подразделения, удовлетворяющего заданным параметрам
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<Address> getAddresses(1:i32 orgStructureId, 2:bool recursive, 3:string infisCode)
    throws (1:SQLException excsql, 2:NotFoundException exc);

/**
 * Получение списка идентификаторов подразделений, расположенных по указанному адресу
 * @param params                        1) Структура с параметрами поиска подразделений по адресу
 * @return                              Список идентификаторов подразделений, приписанных к запрошенному адресу
 * @throws NotFoundException             когда не было найдено ни одного подразделения, удовлетворяющего заданным параметрам
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<i32> findOrgStructureByAddress(1:FindOrgStructureByAddressParameters params)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Получение списка персонала, работающего в запрошенном подразделении
 * @param orgStructureId                1) идентификатор подразделения
 * @param recursive                     2) флаг рекусрии
 * @param infisCode                     3) инфис-код
 * @return                              Список идентификаторов подразделений, приписанных к запрошенному адресу
 * @throws NotFoundException             когда не было найдено ни одного работника, удовлетворяющего заданным параметрам
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<Person> getPersonnel(1:i32 orgStructureId, 2:bool recursive, 3:string infisCode)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * НЕ РЕАЛИЗОВАНО
 */
TicketsAvailability getTotalTicketsAvailability(1:GetTicketsAvailabilityParameters params)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * НЕ РЕАЛИЗОВАНО
 */
list<ExtendedTicketsAvailability> getTicketsAvailability(1:GetTicketsAvailabilityParameters params)
    throws (1:NotFoundException exc, 2:SQLException excsql);

// @deprecated                          В дальнейшем планируется перейти на метод getPersonSchedule
/**
 * Получение расписания врача
 * @param params                        1) Структура с параметрами для получения расписания врача
 * @return                              Структура с расписанием врача (на запрошенный день)
 * @throws NotFoundException             когда не было найдено расписания на запрошенную дату
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
Amb getWorkTimeAndStatus(1:GetTimeWorkAndStatusParameters params)
    throws (1:NotFoundException exc, 2:SQLException excsql, 3:ReasonOfAbsenceException raExc);

/**
 * добавление нового пациента в БД ЛПУ
 * @param params                        1) Структура с данными для нового пациента
 * @return                              Структура со сведениями о статусе добавления пациента
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
PatientStatus addPatient(1:AddPatientParameters params)
    throws (1:SQLException excsql);

/**
 * Поиск пациента в БД ЛПУ по заданным параметрам
 * @param params                        1) Структура с данными для поиска единственного пациента
 * @return                              Структура с данными о результатах посика пациента
 * @throws NotFoundException             //TODO
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
PatientStatus findPatient(1:FindPatientParameters params)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Поиск пациентов в БД ЛПУ по заданным параметрам
 * @param params                        1) Структура с данными для поиска нескольких пациентов
 * @return                              Список структур с данными для найденных пациентов
 * @throws NotFoundException             //TODO
 * @throws SQLException                  когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<Patient> findPatients(1:FindMultiplePatientsParameters params)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Поиск пациента по данным из ТФОМС
 * @param params                        1) Параметры поиска
 * @return                              Статус нахождения пациента
 * @throws NotFoundException            когда не найдено ни одного пациента по заданным параметрам
 * @throws InvalidPersonalInfo          когда по полису или документу найдены пациент(ы) в БД ЛПУ, но (ФИО/пол/др) отличаются от переданных
 * @throws InvalidDocumentException     когда не найдено совпадений по полису и документу, но пациент с таким (ФИО/пол/др) уже есть в БД ЛПУ
 * @throws AnotherPolicyException       когда пациент найден и документы совпали, но его полис отличается от запрошенного
 * @throws NotUniqueException           когда по запрошенным параметрам невозможно выделить единственного пациента
 */
PatientStatus findPatientByPolicyAndDocument(1:FindPatientByPolicyAndDocumentParameters params)
	throws (
		1:NotFoundException nfExc,
		2:InvalidPersonalInfoException invInfoExc,
		3:InvalidDocumentException invDocExc,
		4:AnotherPolicyException anotherPolExc,
		5:NotUniqueException nUniqueExc
	);

/**
 * Добавление/ изменение полиса клиента
 * @param params                        1) Параметры для добавления полиса (struct ChangePolicyParameters)
 * @return                              успешность замены/добавления полиса
 * @throws PolicyTypeNotFoundException  когда нету типа полиса с переданным кодом
 * @throws NotFoundException            когда нету пациента с переданным идентификатором
 */
bool changePatientPolicy(1:ChangePolicyParameters params)
    throws (1:PolicyTypeNotFoundException ptnfExc, 2:NotFoundException nfExc);

/**
 * Запрос на список талончиков, которые появились с момента последнего запроса
 *(для поиска записей на прием к врачу созданных не через КС)
 * @return                              Список новых талончиков или пустой список, если таких талончиков не найдено то пустой список
 */
list<QueueCoupon> checkForNewQueueCoupons();

/**
 * Метод для получения первого свободного талончика врача
 * @param params                        1) Параметры для поиска первого свободого талончика
 * @return                              Структура с данными первого доступного для записи талончика
 * @throws NotFoundException            когда у выьранного врача с этой даты нету свободных талончиков
 */
TTicket getFirstFreeTicket(1:ScheduleParameters params)
    throws (1:NotFoundException nfExc);

/**
 * Метод для получения расписания врача пачкой за указанный интервал
 * @param params                        1) Параметры для получения расписания
 * @return                              структура данных с информацией о примемах врача
 * @throws NotFoundException            когда нету такого идентификатора врача
 */

PersonSchedule getPersonSchedule(1:ScheduleParameters params)
    throws (1:NotFoundException nfExc);

/**
 * Получение детальной информации по пациентам по их идентфикаторам
 * @param patientIds                    1) Список идентификаторов пациентов
 * @return                              map<int, PatientInfo> - карта вида <[Идетификатор пациента], [Информация о пациенте]>,
                                        в случае отсутвия идентификатора в БД ЛПУ набор ключ-значение опускается
 * @throws NotFoundException            //TODO
 * @throws SQLException                 когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
map<i32, Patient> getPatientInfo(1:list<i32> patientIds)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Получение контактной информации для заданного пациента
 * @param patientIds                    1) идентификатор пациентов
 * @return                              Список структур с контактной информацией
 * @throws NotFoundException            //TODO
 * @throws SQLException                 когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<Contact> getPatientContacts(1:i32 patientId)
    throws (1:NotFoundException exc);

/**
 * НЕ РЕАЛИЗОВАНО
 */
list<OrgStructuresProperties> getPatientOrgStructures(1:i32 parentId)
    throws (1:NotFoundException exc);

/**
 * Запись пациента на прием к врачу
 * @param params                        1) Структура с параметрами для  записи на прием к врачу
 * @return                              Структура с данными о статусе записи пациента на прием к врачу
 * @throws NotFoundException            //TODO
 * @throws SQLException                 когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
EnqueuePatientStatus enqueuePatient(1:EnqueuePatientParameters params)
    throws (1:NotFoundException exc, 2:SQLException excsql, 3:ReasonOfAbsenceException raExc);

/**
 * Получение списка записей на приемы к врачам заданного пациента
 * @param patientId                     1) Идентификатор пациента
 * @return                              Список структура с данными о записях пациента на приемы к врачам
 * @throws NotFoundException            //TODO
 * @throws SQLException                 когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
list<Queue> getPatientQueue(1:i32 patientId)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Отмена записи пациента на прием к врачу
 * @param patientId                     1) Идентификатор пациента
 * @param queueId                       2) Идентификатор записи, которую необходимо отменить
 * @return                              Структура с данными о статусе отмены записи пациента на прием к врачу
 * @throws NotFoundException            //TODO
 * @throws SQLException                 когда произошла внутренняя ошибка при запросах к БД ЛПУ
 */
DequeuePatientStatus dequeuePatient(1:i32 patientId, 2:i32 queueId)
    throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Получение списка  с информацией о специализациях и доступных талончиках
 * @param hospitalUidFrom               1) Инфис-код ЛПУ
 * @return                              Список структур с данными о специализациях врачей
 * @throws NotFoundException            когда ничего не найдено
 */
list<Speciality> getSpecialities(1:string hospitalUidFrom)
    throws (1:NotFoundException nfExc);

}