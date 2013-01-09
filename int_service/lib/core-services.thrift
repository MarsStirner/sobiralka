namespace java ru.korus.tmis.communication.thriftgen
//Namespace=package name for java

typedef i64 timestamp


//Type definitions for return structures

struct OrgStructure{
1:required i32 id;
2:optional i32 parent_id=0;
3:required string code;
4:required string name="";
5:optional string adress="";
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
}

struct Amb{
1:optional timestamp begTime;
2:optional timestamp endTime;
3:optional string office;
4:optional string plan;
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
1:optional i32 ticketsPerMonths;
2:optional i32 ticketsAvailable;
3:optional string speciality;
}
//Type definitions for input params

struct FindOrgStructureByAdressParameters{
1:required string pointKLADR;
2:optional string streetKLADR="";
3:optional string number="";
4:optional string corpus="";
5:optional i32 flat=0;
}

struct GetTimeWorkAndStatusParameters{
1:optional i32 hospitalUidFrom;
2:required i32 personId;
3:optional timestamp date;
}

struct AddPatientParameters{
1:optional string lastName;
2:optional string firstName;
3:optional string patrName;
4:optional timestamp birthDate;
}

struct EnqueuePatientParameters{
1:required i32 patientId;
2:required i32 personId;
3:optional timestamp dateTime;
4:optional string note;
5:optional i32 hospitalUidFrom;
}

struct FindPatientParameters{
1:optional string lastName;
2:optional string firstName;
3:optional string patrName;
4:optional timestamp birthDate;
5:optional i32 sex;
6:optional i32 identifierType;
7:required i32 identifier;
8:optional string omiPolicy;
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
list<OrgStructure> getOrgStructures(1:i32 parent_id, 2:bool recursive)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<i32> findOrgStructureByAddress(1:FindOrgStructureByAdressParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Person> getPersonnel(1:i32 orgStructureId, 2:bool recursive)
throws (1:NotFoundException exc, 2:SQLException excsql);

Amb getWorkTimeAndStatus(1:GetTimeWorkAndStatusParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

PatientStatus addPatient(1:AddPatientParameters params)
throws (1:SQLException excsql);

PatientStatus findPatient(1:FindPatientParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<i32> findPatients(1:FindPatientParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<PatientInfo> getPatientInfo(1:list<i32> patientIds)
throws (1:NotFoundException exc, 2:SQLException excsql);

EnqueuePatientStatus enqueuePatient(1:EnqueuePatientParameters params)
throws (1:NotFoundException exc, 2:SQLException excsql);

list<Queue> getPatientQueue(1:i32 parentId)
throws (1:NotFoundException exc, 2:SQLException excsql);

DequeuePatientStatus dequeuePatient(1:i32 patientId, 2:i32 queueId)
throws (1:NotFoundException exc, 2:SQLException excsql);

}