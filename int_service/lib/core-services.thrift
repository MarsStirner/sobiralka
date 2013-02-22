namespace java ru.korus.tmis.communication.thriftgen
//Namespace=package name for java

typedef i64 timestamp


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

struct AddPatientParameters{
1:optional string lastName;
2:optional string firstName;
3:optional string patrName;
4:optional timestamp birthDate;
5:optional i32 sex;
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

//Exceptions
exception NotFoundException {
 1: string error_msg;
}
exception SQLException {
  1: i32 error_code;
  2: string error_msg;
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