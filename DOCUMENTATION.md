Использование интеграционного сервера (ИС)
=================
ИС предоставляет единый SOAP-интерфейс взаимодействия с ФТМИС(6098), НТК, Интрамед.

Ниже описаны доступные вэб-сервисы, предоставляемые ИС.

Получение списка регионов, списка ЛПУ и списка врачей (ListService)
-----------
wsdl сервиса доступна по адресу:
http://SOAP_SERVER_HOST:SOAP_SERVER_PORT/list/?wsdl (например, http://10.1.2.107:9911/list/?wsdl)

**Сервис реализует следующие методы:**

```
listRegions
Формирует и возвращает список регионов, с которыми работает ИС

Return:
        Структура с атрибутом regions, содержащим список регионов:
        Struct.regions =
            [{'name': Наименование региона,
              'code': код региона,},
            ...
            {'name': Наименование региона,
              'code': код региона,},
            ]
```

```
listHospitals
    Формирует и возвращает список ЛПУ и подразделений

    Args:
        Словарь аргументов:
        {'hospitalUid': строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный)
        'speciality': врачебная специальность для фильтрации ЛПУ (необязательный)
        'ocatoCode': код ОКАТО для фильтрации ЛПУ (необязательный)
        }

    Return:
        Структура с атрибутом hospitals, содержащим список ЛПУ:
        Struct.hospitals =
            [{'uid': Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
              'name': Наименование ЛПУ,
              'phone': Номер телефона ЛПУ,
              'address': Адрес ЛПУ,
              'token': Токен ЛПУ,
              'key': Инфис-код ЛПУ
              },
            ...
            {'uid': Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
             'name': Наименование ЛПУ,
             'phone': Номер телефона ЛПУ,
             'address': Адрес ЛПУ,
             'token': Токен ЛПУ,
             'key': Инфис-код ЛПУ
             },
            ]
```

```
listDoctors
    Формирует и возвращает список врачей

    Args:
        Словарь вида:
        {'searchScope':
            {
            'hospitalUid': uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный),
            'address': адрес пациента, для выборки ЛПУ (необязательный),
                {'parsedAddress':
                    {'flat': номер квартиры,
                    'house':{
                        'number': Номер дома
                        'building': Указание на литеру, корпус, строение
                    }
                    'block': Номер квартала (для муниципальных образований,
                        в которых адресация зданий производится с помощью кварталов, а не улиц)
                    'kladrCode': Идентификатор по классификатору КЛАДР
                    }
                }
            }
        'speciality': специальность врача (необязательный),
        'lastName': фамилия врача (необязательный),
        }

    Return:
        Структура с атрибутом doctors (содержащим список врачей) и атрибутом hospitals(содержащим список соответствующих ЛПУ):
        Struct.doctors =
            [{'uid': Уникальный идентификатор врача в Реестре КС,
              'name': {
                  'firstName': Имя,
                  'patronymic': Отчество,
                  'lastName': Фамилия,
                  },
              'hospitalUid': Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
              'speciality': специальность врача,
              'keyEPGU': ключ ЕПГУ,
              },
              ...
            {'uid': Уникальный идентификатор врача в Реестре КС,
             'name': {
                 'firstName': Имя,
                 'patronymic': Отчество,
                 'lastName': Фамилия,
                 },
             'hospitalUid': Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
             'speciality': специальность врача,
             'keyEPGU': ключ ЕПГУ,
             },
            ]
        Struct.hospitals =
            [{'uid': , Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
              'name': , Наименование ЛПУ,
              'phone': , Номер телефона ЛПУ,
              'address': , Адрес ЛПУ,
              'token': , Токен ЛПУ,
              'key': , Инфис-код ЛПУ
              },
            ...
            {'uid': , Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
             'name': , Наименование ЛПУ,
             'phone': , Номер телефона ЛПУ,
             'address': , Адрес ЛПУ,
             'token': , Токен ЛПУ,
             'key': , Инфис-код ЛПУ
             },
            ]
```

Получение подробной информации об ЛПУ (InfoService)
-----------
wsdl сервиса доступна по адресу:
http://SOAP_SERVER_HOST:SOAP_SERVER_PORT/info/?wsdl (например, http://10.1.2.107/info/?wsdl)

**Сервис реализует следующие методы:**

```
getHospitalInfo
    Возвращает список ЛПУ и подразделений по переданным параметрам

    Args:
        Словарь вида:
        {'hospitalUid': строка или массив строк вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (необязательный)}

    Return:
        Структура с атрибутом info, содержащим список ЛПУ и их подразделений:
        Struct.info =
            [{'uid': Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
              'name': Наименование ЛПУ,
              'type': Тип ЛПУ: (Поликлиника) (не заполняется),
              'phone': Номер телефона ЛПУ,
              'email': Адрес электронной почты ЛПУ,
              'siteURL': '' (не заполняется),
              'schedule': Расписание работы (не заполняется),
              'buildings': Подразделения ЛПУ:
                    [{'id': id Подразделения в БД КС,
                    'uid': Уникальный идентификатор подразделения в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
                    'name': Наименование объекта (корпуса, отделения) ЛПУ, расположенных по данному адресу,
                    'address': Почтовый адрес объекта,
                    'phone': Телефон объекта,
                    'schedule': Расписание работы (не заполняется),
                    }
                    ...
                    {'id': id Подразделения в БД КС,
                    'uid': Уникальный идентификатор подразделения в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
                    'name': Наименование объекта (корпуса, отделения) ЛПУ, расположенных по данному адресу,
                    'address': Почтовый адрес объекта,
                    'phone': Телефон объекта,
                    'schedule': Расписание работы (не заполняется),
                    }
                    ],
              },
            ...
             {'uid': Уникальный идентификатор ЛПУ в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
              'name': Наименование ЛПУ,
              'type': Тип ЛПУ: (Поликлиника) (не заполняется),
              'phone': Номер телефона ЛПУ,
              'email': Адрес электронной почты ЛПУ,
              'siteURL': '' (не заполняется),
              'schedule': Расписание работы (не заполняется),
              'buildings': Подразделения ЛПУ:
                    [{'id': id Подразделения в БД КС,
                    'uid': Уникальный идентификатор подразделения в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
                    'name': Наименование объекта (корпуса, отделения) ЛПУ, расположенных по данному адресу,
                    'address': Почтовый адрес объекта,
                    'phone': Телефон объекта,
                    'schedule': Расписание работы (не заполняется),
                    }
                    ...
                    {'id': id Подразделения в БД КС,
                    'uid': Уникальный идентификатор подразделения в рамка ИС, вида: 'LPU_ID/LPU_Unit_ID',
                    'name': Наименование объекта (корпуса, отделения) ЛПУ, расположенных по данному адресу,
                    'address': Почтовый адрес объекта,
                    'phone': Телефон объекта,
                    'schedule': Расписание работы (не заполняется),
                    }
                    ],
              },
              ]
```

Работа с расписанием (ScheduleService)
-----------
wsdl сервиса доступна по адресу:
http://SOAP_SERVER_HOST:SOAP_SERVER_PORT/schedule/?wsdl (например, http://10.1.2.107/schedule/?wsdl)

**Сервис реализует следующие методы:**

```
getScheduleInfo
    Возвращает расписание врача на указанный диапазон дат

    Args:
        Словарь вида:
            {'hospitalUid': uid ЛПУ, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            'doctorUid': uid врача (обязательный)
            'speciality': наименование врачебной специальности (необязательный)
            'hospitalUidFrom': id ЛПУ, из которого предполагается запись (необязательный)
            }

    Return:
        Структура с атрибутом timeslots, содержащим список талончиков к врачу
        Struct.timeslots =
            [{'start': Время начала талончика,
              'finish': Время окончания талончика,
              'status': Статус талончика 'free'/'locked' (свободне/занят),
              'office': номер кабинета,
              'patientId': id записанного пациента (если записан),
              'patientInfo': ФИО записанного пациента (если записан),
              },
            ...
             {'start': Время начала талончика,
              'finish': Время окончания талончика,
              'status': Статус талончика 'free'/'locked' (свободне/занят),
              'office': номер кабинета,
              'patientId': id записанного пациента (если записан),
              'patientInfo': ФИО записанного пациента (если записан),
              },
            ]
```

```
getTicketStatus
    Возвращает статус талончиков

    Args:
        Словарь вида:
            {'hospitalUid': uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
             'ticketUid': uid талончика (обязательный), строка вида 'ticket_id/patient_id'
             'lastUid': id талончика, начиная с которого необходимо сделать выборку информации о талончиках,
                 если передан, то ticketUid игнорируется (необязательный)
             }

    Returns:
        Структура с атрибутом ticketsInfo, содержащим список талончиков с подробной информацией
        Struct.ticketsInfo =
            [{'id': Уникальный для ИС идентификатор талончика,
              'ticketUid': Уникальный для МИС ЛПУ идентификатор талончика,
              'hospitalUid': Уникальный идентификатор ЛПУ вида 'LPU_ID/LPU_Unit_ID',
              'doctorUid': Уникальный для МИС ЛПУ идентификатор врача,
              'doctor': {
                  'firstName': Имя врача,
                  'patronymic': Отчество врача,
                  'lastName': Фамилия врача,
              },
              'person': {
                  'firstName': Имя пациента,
                  'patronymic': Отчество пациента,
                  'lastName': Фамилия пациента,
              },
              'status': Статус талончика, один из:
                ('accepted', 'unconfirmed', 'processing', 'rejected', 'forbidden', 'canceledByHospital', 'canceled', 'rescheduled', substituted',),
              'timeslotStart': Начало приёма у врача,
              'comment':Дополнительные указания и информация,
              'location': Информация о месте приёма (название ЛПУ и адрес),
              },
            ...
            ]
```

```
enqueue
    Запись на приём

    Args:
        Словарь вида:
            {'person': словарь с данными о пациенте (обязательный):
                 {'lastName': фамилия
                 'firstName': имя
                 'patronymic': отчество
                 }
            'hospitalUid': uid ЛПУ или подразделения, строка вида: '17/0', соответствует 'LPU_ID/LPU_Unit_ID' (обязательный)
            'birthday': дата рождения пациента (обязательный)
            'doctorUid': id врача, к которому производится запись (обязательный)
            'omiPolicyNumber': номер полиса мед. страхования (обязательный)
            'timeslotStart': время записи на приём (обязательный)
            'hospitalUidFrom': uid ЛПУ, с которого производится запись (необязательный), используется для записи между ЛПУ
            }

    Returns:
        Структура с атрибутами:
        Struct.result - результат записи True/False
        Struct.message - сообщение об ошибке записи или успешной записи
        Struct.ticketUid - id талончика
```
---------------------------------

Запись между ЛПУ
=================

В силу того, что ИС является связующим звеном между ЛПУ и работает через свой внутренний реестр больниц, для записи между ЛПУ следует придерживаться следующего алгоритма:

1. Получить список ЛПУ из ИС, вызвав по SOAP метод listHospitals.

2. *Для выбранного ЛПУ получить список врачей, вызвать по SOAP метод listDoctors, использовав в качестве параметра hospitalUid, предоставляемый ИС.

3. *Получить расписание врача, SOAP метод getScheduleInfo. В качестве doctorUid используется id врача в рамках ЛПУ.

4. Записать пациента на приём к врачу на выбранное время, SOAP метод enqueue.

* - Т.к. в качестве id врача используется реальный id из БД ЛПУ, а не внутренний id ИС, то шаги 2 и 3 могут быть пропущены, в случае если известен врач и время, на которое предполагается запись.

Во всех методах в качестве hospitalUid используется внутренний id из реестра ЛПУ в БД ИС, т.к. БД ИС хранит информацию о КС конкретных ЛПУ.
