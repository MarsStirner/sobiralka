namespace java ru.korus.tmis.communication.thriftgen
//Namespace=package name for java

typedef i64 timestamp
typedef i16 short


//Type definitions for return structures

struct Organization{
1:required string fullName;
2:optional string shortName;
3:optional string address;
4:required string infisCode;
}

struct OrgStructure{
1:required i32 id;
2:optional i32 parent_id=0;
3:required string code;
4:required string name="";
5:optional string address="";
6:optional string sexFilter="";
7:optional string ageFilter="";
}

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
12:optional string SexFilter;
}

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

struct Amb{
1:optional timestamp begTime;
2:optional timestamp endTime;
3:optional string office;
4:optional i32 plan;
5:optional list<Ticket> tickets;
6:optional i32 available;
}

struct PatientStatus{
1:required bool success;
2:optional string message;
3:optional i32 patientId;
}

struct PatientInfo{
1:optional string lastName;
2:optional string firstName;
3:optional string patrName;
4:optional timestamp birthDate;
5:optional i32 sex;
}

struct Patient{
1:required i32 id;
2:optional string lastName;
3:optional string firstName;
4:optional string patrName;
5:optional timestamp birthDate;
6:optional i32 sex;
}

struct OrgStructuresProperties{
1:required i32 orgStructureId;
2:optional bool attached;
3:optional bool matchRegAddress;
4:optional bool matchLocAddress;
}


struct EnqueuePatientStatus{
1:required bool success;
2:optional string message;
3:optional i32 index;
4:optional i32 queueId;
}

struct Queue{
1:optional timestamp dateTime;
2:optional i32 index;
3:optional i32 personId;
4:optional string note;
5:optional i32 queueId;
6:optional i32 enqueuePersonId;
7:optional timestamp enqueueDateTime;
}

struct DequeuePatientStatus{
1:required bool success;
2:optional string message;
}

struct Speciality{
1:required i32 id;
2:optional i32 ticketsPerMonths;
3:optional i32 ticketsAvailable;
4:optional string speciality;
}

struct Address{
1:required i32 orgStructureId;
2:required string pointKLADR;
3:required string streetKLADR;
4:optional string number;
5:optional string corpus;
6:optional i32 firstFlat;
7:optional i32 lastFlat;
}

struct Contact{
1:optional string type;
2:optional string code;
3:optional string contact;
4:optional string note;
}

//Type definitions for input params

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
 * AddPatientParameters 	Структура для создания нового пациента
 * @param lastName			Фамилия пациента
 * @param firstName			Имя пациента
 * @param patrName			Отчество пациента
 * @param birthDate			Дата рождения пациента
 * @param sex				Пол пациента
 * @param documentSerial	Серия документа
 * @param documentNumber	Номер документа
 * @param documentTypeCode	Код типа документа
 * @param policySerial		Серия полиса
 * @param policyNumber		Номер полиса
 * @param policyTypeCode	Код типа полиса
 * @param policyInsurerInfisCode	Инфис код страховой, полис которой представлен выше
 */
 
struct AddPatientParameters{
1:optional string lastName;
2:optional string firstName;
3:optional string patrName;
4:optional timestamp birthDate;
5:optional i32 sex;
//Version 2
6:required string documentSerial;
7:required string documentNumber;
8:required string documentTypeCode;
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
 * @param lastName			1)Фамилия пациента
 * @param firstName			2)Имя пациента
 * @param patrName			3)Отчество пациента
 * @param sex				4)Пол пациента
 * @param birthDate			5)Дата рождения пациента
 * @param documentSerial	6)Серия документа
 * @param documentNumber	7)Номер документа
 * @param documentTypeCode	8)Код типа документа
 * @param policySerial		9)Серия полиса
 * @param policyNumber		10)Номер полиса
 * @param policyTypeCode	11)Код типа полиса
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

//Exceptions
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

//Service to be generated from here
service Communications{

//Methods to be generated in this service

Organization getOrganisationInfo(1:string infisCode)
throws (1:NotFoundException exc);

list<OrgStructure> getOrgStructures(1:i32 parent_id, 2:bool recursive, 3:string infisCode)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Address> getAddresses(1:i32 orgStructureId, 2:bool recursive, 3:string infisCode)
throws (1:SQLException excsql, 2:NotFoundException exc);

list<i32> findOrgStructureByAddress(1:FindOrgStructureByAddressParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Person> getPersonnel(1:i32 orgStructureId, 2:bool recursive, 3:string infisCode)
throws (1:NotFoundException exc, 2:SQLException excsql);

TicketsAvailability getTotalTicketsAvailability(1:GetTicketsAvailabilityParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<ExtendedTicketsAvailability> getTicketsAvailability(1:GetTicketsAvailabilityParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

Amb getWorkTimeAndStatus(1:GetTimeWorkAndStatusParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

PatientStatus addPatient(1:AddPatientParameters params)
throws (1:SQLException excsql);


PatientStatus findPatient(1:FindPatientParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Patient> findPatients(1:FindMultiplePatientsParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

/**
 * Поиск пациента по данным из ТФОМС
 * @param params Параметры поиска
 * @return Статус нахождения пациента
 * @throws NotFoundException когда не найдено ни одного пациента по заданным параметрам
 * @throws InvalidPersonalInfo когда по полису или документу найдены пациент(ы) в БД ЛПУ, но (ФИО/пол/др) отличаются от переданных
 * @throws InvalidDocumentException когда не найдено совпадений по полису и документу, но пациент с таким (ФИО/пол/др) уже есть в БД ЛПУ
 * @throws AnotherPolicyException когда пациент найден и документы совпали, но его полис отличается от запрошенного
 * @throws NotUniqueException когда по запрошенным параметрам невозможно выделить единственного пациента
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
 * @param params                    1) Параметры для добавления полиса (struct ChangePolicyParameters)
 * @return успешность замены/добавления полиса
 * @throws PolicyTypeNotFoundException когда нету типа полиса с переданным кодом
 * @throws NotFoundException когда нету пациента с переданным идентификатором
 */
bool changePatientPolicy(1:ChangePolicyParameters params)
    throws (1:PolicyTypeNotFoundException ptnfExc, 2:NotFoundException nfExc);

map<i32,PatientInfo> getPatientInfo(1:list<i32> patientIds)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Contact> getPatientContacts(1:i32 patientId)
throws (1:NotFoundException exc);

list<OrgStructuresProperties> getPatientOrgStructures(1:i32 parentId)
throws (1:NotFoundException exc);

EnqueuePatientStatus enqueuePatient(1:EnqueuePatientParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Queue> getPatientQueue(1:i32 parentId)
throws (1:NotFoundException exc, 2:SQLException excsql);

DequeuePatientStatus dequeuePatient(1:i32 patientId, 2:i32 queueId)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Speciality> getSpecialities(1:string hospitalUidFrom)
throws (1:SQLException exc);

}