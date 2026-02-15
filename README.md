# yakafka-p5

## Содержание

- [1. Разворачиваем проект, проверяем общую работоспособность](#deploy)
    - [1.1. Копируем файлы на хостовую машину и запускаем проект](#deploy_compose_up)
    - [1.2. Проверяем, что контейнеры не упали после запуска](#deploy_test_ps)
    - [1.3. Смотрим доступность необходимых UI по http](#deploy_test_ui)
    - [1.4. Убеждаемся, что таблицы созданы и заполнены](#deploy_test_db)
- [2. Создаём и тестируем коннектор](#connector)
    - [2.1. Создаём коннектор через http-запрос к Kafka Connect REST API](#connector_post)
    - [2.2. Проверим статус коннектора по http API](#connector_status)
    - [2.3. Проверим коннектор в UI Debezium-а](#connector_check_ui)
    - [2.4. Проверим топики в Kafka UI](#connector_topics)
- [3. Проверяем log-based CDC](#cdc)
    - [3.1. Нагружаем postgres на запись](#cdc_insert)
    - [3.2. Проверим топики в Kafka UI](#cdc_topic)
- [4. Проверяем Мониторинг](#monitoring)
- [5. Приложение на python](#python_app)
    - [5.1. Поработаем руками с ksqldb](#python_app_ksql)
- [6. Ресерч: Инкрементальные снапшоты по сигналам](#signal)
    - [6.1. Перезапускаем проект](#signal_restart)
    - [6.2. Убедимся, что создалась таблица customers.public.debezium_signal](#signal_rdbms_ddl)
    - [6.3. Создаём коннектор со снапшотом no_data и конфигурацией сигналов](#signal_connector)
    - [6.4. Убедимся, что не был сделан initial snapshot](#signal_initial_snapshot)
    - [6.5. Создадим топик customers_signaling_topic](#signal_topic)
    - [6.6. Отправим сигнал на создание инкрементного снапшота](#signal_message)
    - [6.7. Смотрим в логи Kafka Connect](#signal_logs)
    - [6.8. Проверим топики в Kafka UI](#signal_topics)
    - [6.9. Посмотрим, что ОНО напихало в рсубд](#signal_rdbms_dml)
    - [6.10. Итого](#signal_summary)

## <a name="deploy">1. Разворачиваем проект, проверяем общую работоспособность</a>

### <a name="deploy_compose_up">1.1. Копируем файлы на хостовую машину и запускаем проект</a>

**Notes**:

- Допустим, у нас клиентская машина называется `VonBraun`, а хостовая машина называется `tesla` и доступна по http как `192.168.100.225`; docker доступен через `sudo` и т.д. (ниже в иллюстрациях исходим из этого).
- Пути и версии образов для проекта описаны переменными окружения в файле `.env.793`. Версия Кафки получится `3.9`.
- Режим кластера - `Kraft`.
- Многие порты "наружу" переопределены для многих сервисов относительно портов по умолчанию, во избежание конфликтов (ниже будет список url-ов для проверок по http).
- Структура БД и инициализационное наполнение данных создаётся при разворачивании проекта, как и "логическая" репликация посгреса (см. `./postgres/custom-config.conf`, `./postgres/init-scripts/create_tables.sql` и соотв. инструкции в `./docker-compose.yaml`).
- Коннекторы будем создавать и удалять руками, конфиги находятся в файлах `./connector.json`, `./connector4signals.json` (второй - для тестирования инкрементных снапшотов по сигналам).
- "Давать нагрузку" на postgres для тестирования cdc и графаны будем руками.

**NB**: для разворачивания контейнера с Grafana на хостовой машине должен быть доступен глобальный интернет из незаблоченной им юрисдикции. **TODO**: убрать инструкцию по установке пайчарта в Графану и посмотреть, будет ди работоспособен проект в части соответствия ТЗ.

```bash
vonbraun@VonBraun:/.../ya_kafka_project5$ ssh -p 2222 tesla@192.168.100.225
...
tesla@tesla:~$ cd /.../ya_kafka_project5
...
tesla@tesla:/.../ya_kafka_project5$ sudo docker compose --env-file .env.793 up -d --build
...
[+] up 20/20
 ✔ Image ya_kafka_project5-grafana                   Built    1.0s
 ✔ Image ya_kafka_project5-kafka-connect             Built    1.0s
 ✔ Network custom_network                            Created  0.0s
 ✔ Volume ya_kafka_project5_kafka_0_data             Created  0.0s
 ✔ Volume ya_kafka_project5_kafka_1_data             Created  0.0s
 ✔ Volume ya_kafka_project5_kafka_2_data             Created  0.0s
 ✔ Volume ya_kafka_project5_ksqldb_server_extensions Created  0.0s
 ✔ Volume ya_kafka_project5_postgres_data            Created  0.0s
 ✔ Container yakafka-p5-grafana                      Created  0.1s
 ✔ Container yakafka-p5-kafka-1                      Created  0.1s
 ✔ Container yakafka-p5-postgres                     Created  0.1s
 ✔ Container yakafka-p5-debezium-ui                  Created  0.1s
 ✔ Container yakafka-p5-kafka-2                      Created  0.1s
 ✔ Container yakafka-p5-kafka-ui                     Created  0.1s
 ✔ Container yakafka-p5-kafka-0                      Created  0.1s
 ✔ Container yakafka-p5-schema-registry              Created  0.0s
 ✔ Container yakafka-p5-ksqldb-server                Created  0.1s
 ✔ Container yakafka-p5-kafka-connect                Created  0.0s
 ✔ Container yakafka-p5-prometheus                   Created  0.0s
 ✔ Container yakafka-p5-ksqldb-cli                   Created  0.0s
```

### <a name="deploy_test_ps">1.2. Проверяем, что контейнеры не упали после запуска</a>

```bash
# {{.ID}}, {{.Image}}, {{.Command}}, {{.CreatedAt}}, {{.RunningFor}}, {{.Ports}}, {{.Status}}, {{.Size}}, {{.Names}}, {{.Labels}}, {{.Mounts}}, {{.Networks}}

tesla@tesla:/.../ya_kafka_project5$ sudo docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Networks}}"
NAMES                        STATUS                   NETWORKS
yakafka-p5-ksqldb-cli        Up 6 minutes             custom_network
yakafka-p5-prometheus        Up 6 minutes             custom_network
yakafka-p5-kafka-connect     Up 6 minutes (healthy)   custom_network
yakafka-p5-ksqldb-server     Up 6 minutes             custom_network
yakafka-p5-schema-registry   Up 6 minutes             custom_network
yakafka-p5-kafka-1           Up 6 minutes             custom_network
yakafka-p5-kafka-0           Up 6 minutes             custom_network
yakafka-p5-kafka-2           Up 6 minutes             custom_network
yakafka-p5-postgres          Up 6 minutes             custom_network
yakafka-p5-debezium-ui       Up 6 minutes             custom_network
yakafka-p5-kafka-ui          Up 6 minutes             custom_network
yakafka-p5-grafana           Up 6 minutes             custom_network
```

TODO: префикс `yakafka-p5` вынести в `--project-name` (`name: yakafka-p5` над `services:`.).

### <a name="deploy_test_ui">1.3. Смотрим доступность необходимых UI по http</a>

* `http://192.168.100.225:3000/` - `Grafana` запросила креденшлы (`admin:admin`)
* `http://192.168.100.225:9090/` - `Prometheus` отрисовал "No data queried yet"
* `http://192.168.100.225:9876/` - `Kafka Connect` выдал какие-то логи/метрики
* `http://192.168.100.225:8070/`, `http://192.168.100.225:8070/ui/clusters/p5/all-topics` - `Kafka UI` видит кластер `p5` и системные топики кафки, коннекта, ksql
* `http://192.168.100.225:8060/` - Debezium UI увидел `http://kafka-connect:8083`, отразил отсутствие коннекторов ("No connectors")

### <a name="deploy_test_db">1.4. Убеждаемся, что таблицы созданы и заполнены</a>

1. **NB**: Таблицы созданы с FK-констрайнтами, поэтому позже при транкейте используем `TRUNCATE ... CASCADE`.
2. **NB**: Автосоздание таблиц работает только если volume с данными постгреса (см. `postgres_data:/var/lib/postgresql/data` в `./docker-compose.yaml`) пуст, то есть при первом запуске проекта или запуске после `down -v`, поэтому если надо пересоздавать структуру руками - см. `./postgres/init-scripts/create_tables.sql`.

```bash
tesla@tesla:/.../ya_kafka_project5$ sudo docker exec -it yakafka-p5-postgres psql -h 127.0.0.1 -U postgres-user -d customers
psql (16.4 (Debian 16.4-1.pgdg110+2))
Type "help" for help.

customers=# \d public.users
  Table "public.users"
   Column   |            Type             | Nullable |              Default              
------------+-----------------------------+----------+-----------------------------------
 id         | integer                     | not null | nextval('users_id_seq'::regclass)
 name       | character varying(100)      |          | 
 email      | character varying(100)      |          | 
 created_at | timestamp without time zone |          | CURRENT_TIMESTAMP
Indexes:
    "users_pkey" PRIMARY KEY, btree (id)
Referenced by:
    TABLE "orders" CONSTRAINT "orders_user_id_fk_users_id" FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE

customers=# \d public.orders
  Table "public.orders"
    Column    |            Type             | Nullable |              Default               
--------------+-----------------------------+----------+------------------------------------
 id           | integer                     | not null | nextval('orders_id_seq'::regclass)
 user_id      | integer                     |          | 
 product_name | character varying(100)      |          | 
 quantity     | integer                     |          | 
 order_date   | timestamp without time zone |          | CURRENT_TIMESTAMP
Indexes:
    "orders_pkey" PRIMARY KEY, btree (id)
Foreign-key constraints:
    "orders_user_id_fk_users_id" FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE

customers=# SELECT * FROM users;
 id |     name      |       email       |         created_at         
----+---------------+-------------------+----------------------------
  1 | John Doe      | john@example.com  | 2026-02-14 13:50:46.617748
  2 | Jane Smith    | jane@example.com  | 2026-02-14 13:50:46.617748
  3 | Alice Johnson | alice@example.com | 2026-02-14 13:50:46.617748
  4 | Bob Brown     | bob@example.com   | 2026-02-14 13:50:46.617748
(4 rows)

customers=# SELECT * FROM orders;
 id | user_id | product_name | quantity |         order_date         
----+---------+--------------+----------+----------------------------
  1 |       1 | Product A    |        2 | 2026-02-14 13:50:46.620269
  2 |       1 | Product B    |        1 | 2026-02-14 13:50:46.620269
  3 |       2 | Product C    |        5 | 2026-02-14 13:50:46.620269
  4 |       3 | Product D    |        3 | 2026-02-14 13:50:46.620269
  5 |       4 | Product E    |        4 | 2026-02-14 13:50:46.620269
(5 rows)

customers=#
```

## <a name="connector">2. Создаём и тестируем коннектор</a>

### <a name="connector_post">2.1. Создаём коннектор через http-запрос к Kafka Connect REST API</a>

Сначала сделаем `DELETE`, так как `PUT` и `PATCH` не прокатывают к коллекции коннекторов
(`405`-й http-статус ответа: Not Allowed).

В первый раз ожидаемо получим `404`, но для порядку всё равно делаем.

```bash
tesla@tesla:/.../ya_kafka_project5$ curl -sX DELETE http://localhost:8073/connectors/pg-connector | jq
{
  "error_code": 404,
  "message": "Connector pg-connector not found"
}
```

Теперь добавим `POST`-ом.

```bash
# 8073
tesla@tesla:/.../ya_kafka_project5$ curl -sX POST -H 'Content-Type: application/json' --data @connector.json http://localhost:8073/connectors | jq
{
  "name": "pg-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres-user",
    "database.password": "postgres-pw",
    "database.dbname": "customers",
    "table.include.list": "public.users,public.orders",
    "column.mask.with.3.chars": "public.users.email,public.users.name",
    "heartbeat.interval.ms": "30000",
    "snapshot.mode": "initial",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "topic.prefix": "customers",
    "topic.creation.enable": "true",
    "topic.creation.default.replication.factor": "-1",
    "topic.creation.default.partitions": "-1",
    "skipped.operations": "none",
    "name": "pg-connector"
  },
  "tasks": [],
  "type": "source"
}
```

### <a name="connector_status">2.2. Проверим статус коннектора по http API</a>

```bash
tesla@tesla:/.../ya_kafka_project5$ curl -s GET http://localhost:8073/connectors/pg-connector/status | jq
{
  "name": "pg-connector",
  "connector": {
    "state": "RUNNING",
    "worker_id": "localhost:8083"
  },
  "tasks": [
    {
      "id": 0,
      "state": "RUNNING",
      "worker_id": "localhost:8083"
    }
  ],
  "type": "source"
}
```

### <a name="connector_check_ui">2.3. Проверим коннектор в UI Debezium-а</a>

`http://192.168.100.225:8060/`

| Name | Status | Tasks |
|------|--------|-------|
| pg-connector | RUNNING | 1 (RUNNING : 1) |

### <a name="connector_topics">2.4. Проверим топики в Kafka UI</a>

`http://192.168.100.225:8070/ui/clusters/p5/all-topics?perPage=25`

По идее должен автосоздаться топик для `heartbeat`
и два топика (`"table.include.list": "public.users,public.orders"`)
за счёт `snapshot.mode": "initial"`.

| Topic Name | Partitions | Out of sync replicas | Replication Factor | Number of messages | Size |
|------------|------------|----------------------|--------------------|--------------------|------|
| `IN` `__debezium-heartbeat.customers` | 1 | 0 | 1 | 23 | 10 KB |
| `customers.public.orders` | 1 | 0 | 1 | 5 | 5 KB |
| `customers.public.users` | 1 | 0 | 1 | 4 | 3 KB |

Посмотрим например в сообщения топика `customers.public.users`:

`http://192.168.100.225:8070/ui/clusters/p5/all-topics/customers.public.users/messages?keySerde=String&valueSerde=String&limit=100`

Видим `initial snapshot` на 4 сообщения (см. выше раздел про проверку состояния БД).

Открываем `Value` первого (нолевого) сообщения, видим секцию:

```
...
  "payload": {
    "id": 1,
    "name": "***",
    "email": "***",
    "created_at": 1771077046617748
  }
...
```

**Заодно убедились, что работает настройка коннектора** `"column.mask.with.3.chars": "public.users.email,public.users.name"`.


## <a name="cdc">3. Проверяем log-based CDC</a>

### <a name="cdc_insert">3.1. Нагружаем postgres на запись</a>

```bash
customers=# TRUNCATE table users CASCADE;

NOTICE:  truncate cascades to table "orders"
TRUNCATE TABLE

customers=# INSERT INTO users (id, name, email)
SELECT
   i,
  'user_' || i,
  'user_' || i  || '@example.com'
FROM
   generate_series(1, 100000) AS i;

INSERT 0 100000
```

### <a name="cdc_topic">3.2. Проверим топики в Kafka UI</a>

`http://192.168.100.225:8070/ui/clusters/p5/all-topics?perPage=25`

| Topic Name | Partitions | Out of sync replicas | Replication Factor | Number of messages | Size |
|------------|------------|----------------------|--------------------|--------------------|------|
| `customers.public.users` | 1 | 0 | 1 | 100004 | 84 MB |

Видим 100004 сообщения: 4 от `initial snapshot` и 100000 - `cdc` нашего сиквела пунктом выше.

## 4. <a name="monitoring">Проверяем Мониторинг</a>

**NB**: тут надо выждать какое-то количество минут, чтобы агрегировались наши метрики (видимо).

Идём в `Grafana`:

`http://192.168.100.225:3000/d/kafka-connect-overview-0/kafka-connect-overview-0?orgId=1&from=now-15m&to=now&var-instance=kafka-connect:9876&var-connector=pg-connector`

Видим `General`:

| Tasks Total | Tasks Running | Tasks Paused | Tasks Failed | Tasks Unassigned | Tasks Destroyed |
|-------------|---------------|--------------|--------------|------------------|-----------------|
| 1 | 1 | 0 | 0 | 0 | 0 |

Видим `Connect Worker`:

| instance | Connector Count | Connector Startup Success Total | Connector Startup Failure Total | Number of tasks | Task Startup Success | Task Startup Failure |
|----------|-----------------|---------------------------------|---------------------------------|-----------------|----------------------|----------------------|
| kafka-connect:9876 | 1 | 1 | 0 | 1 | 0 | 0 |

Видим `Connector details`:

| name | Nb of tasks | Nb of Tasks running | Nb of Tasks failed | Nb of Tasks paused | Nb of Tasks destroyed | Nb of Tasks unassigned |
|------|-------------|---------------------|--------------------|--------------------|-----------------------|------------------------|
| pg-connector | 1 | 1 | 0 | 0 | 0 | 0 |

Видим дашбоарды:

- `Source Record Poll rate`: 1.76 Kops/s на пике выброса
- `Source Record Write rate`: 1.76 Kops/s на пике выброса
- `Batch Size Average`: 885 B на пике выброса
- etc.


## <a name = "python_app">5. Приложение на python</a>

В этот раз потренируемся изготовить простое python-приложение, работающее через `ksqldb`.

Сначала осуществим все действия руками через консоль, а потом запустим приложение,
реализующее ровно тот же алгоритм.

**Какая тут у нас тонкость**: надо выгребать из сообщения не только `Value`, но и `Key`,
так как при удалении записи `Value` в cdc message равно `null`,
а `id` удалённой сущности надо искать в `payload` в `Key`.

Как получить `Key` при определении `stream`-а? См. ниже: определяем поле с ключевым словом `KEY`.

### <a name="python_app_ksql">5.1. Поработаем руками с ksqldb</a>

**5.1.1. Заходим в необходимое приложение необходимого контейнера**:

```bash
tesla@tesla:/.../ya_kafka_project5$ sudo docker exec -it yakafka-p5-ksqldb-cli ksql http://ksqldb-server:8088
...
```

**5.1.2. Убедимся, что необходимые топики существуют** (`customers.public.orders`, `customers.public.users`):

```bash
ksql> SHOW TOPICS;

 Kafka Topic                    | Partitions | Partition Replicas 
------------------------------------------------------------------
 __debezium-heartbeat.customers | 1          | 1                  
 connect-config-storage         | 1          | 1                  
 connect-offset-storage         | 25         | 1                  
 connect-status-storage         | 5          | 1                  
 customers.public.orders        | 1          | 1                  
 customers.public.users         | 1          | 1                  
 default_ksql_processing_log    | 1          | 1                  
------------------------------------------------------------------
```

**5.1.3. Дропаем стримы, чтобы далее создать их с чистого листа**:

```bash
ksql> DROP STREAM IF EXISTS cdc_raw_orders;

 Message                                       
-----------------------------------------------
 Source `CDC_RAW_ORDERS` does not exist. 
-----------------------------------------------

ksql> DROP STREAM IF EXISTS cdc_raw_users;

 Message                                
----------------------------------------
 Source `CDC_RAW_USERS` does not exist. 
----------------------------------------

```

**5.1.4. Создадим stream-ы, в которые вытянем payload сообщений как json**

Запросы ksql:

```sql
CREATE STREAM IF NOT EXISTS cdc_raw_users (
  key STRUCT<
    schema VARCHAR,
    payload STRUCT<
      id INT
    >
  > KEY,
  schema VARCHAR,
  payload STRUCT<
    id INT,
    name VARCHAR,
    email VARCHAR,
    created_at BIGINT
  >
) WITH (
  KAFKA_TOPIC = 'customers.public.users',
  VALUE_FORMAT = 'JSON',
  KEY_FORMAT = 'JSON'
);

CREATE STREAM IF NOT EXISTS cdc_raw_orders (
  key STRUCT<
    schema VARCHAR,
    payload STRUCT<
      id INT
    >
  > KEY,
  schema VARCHAR,
  payload STRUCT<
    id INT,
    user_id INT,
    product_name VARCHAR,
    quantity INT,
    order_date BIGINT
  >
) WITH (
  KAFKA_TOPIC = 'customers.public.orders',
  VALUE_FORMAT = 'JSON',
  KEY_FORMAT = 'JSON'
);
```

Консоль:

```bash
ksql> CREATE STREAM IF NOT EXISTS cdc_raw_users (
>  key STRUCT<
>    schema VARCHAR,
>    payload STRUCT<
>      id INT
>    >
>  > KEY,
>  schema VARCHAR,
>  payload STRUCT<
>    id INT,
>    name VARCHAR,
>    email VARCHAR,
>    created_at BIGINT
>  >
>) WITH (
>  KAFKA_TOPIC = 'customers.public.users',
>  VALUE_FORMAT = 'JSON',
>  KEY_FORMAT = 'JSON'
>);

 Message        
----------------
 Stream created 
----------------

ksql> CREATE STREAM IF NOT EXISTS cdc_raw_orders (
>  key STRUCT<
>    schema VARCHAR,
>    payload STRUCT<
>      id INT
>    >
>  > KEY,
>  schema VARCHAR,
>  payload STRUCT<
>    id INT,
>    user_id INT,
>    product_name VARCHAR,
>    quantity INT,
>    order_date BIGINT
>  >
>) WITH (
>  KAFKA_TOPIC = 'customers.public.orders',
>  VALUE_FORMAT = 'JSON',
>  KEY_FORMAT = 'JSON'
>);

 Message        
----------------
 Stream created 
----------------
```

**5.1.5. Streams list:**

```bash
ksql> SHOW STREAMS;

 Stream Name    | Kafka Topic             | Key Format | Value Format | Windowed 
---------------------------------------------------------------------------------
 CDC_RAW_ORDERS | customers.public.orders | JSON       | JSON         | false    
 CDC_RAW_USERS  | customers.public.users  | JSON       | JSON         | false    
---------------------------------------------------------------------------------

```

**5.1.6. Прочитаем по 1-му сообщению с каждого стрима для проверки**:

```bash
ksql> SELECT KEY, PAYLOAD FROM CDC_RAW_USERS LIMIT 1;
+----------------------------------------------------------------+----------------------------------------------------------------+
|KEY                                                             |PAYLOAD                                                         |
+----------------------------------------------------------------+----------------------------------------------------------------+
|{SCHEMA={"type":"struct","fields":[{"type":"int32","optional":fa|{ID=1, NAME=***, EMAIL=***, CREATED_AT=1771174557122423}        |
|lse,"default":0,"field":"id"}],"optional":false,"name":"customer|                                                                |
|s.public.users.Key"}, PAYLOAD={ID=1}}                           |                                                                |
Limit Reached
Query terminated


ksql> SELECT KEY, PAYLOAD FROM CDC_RAW_ORDERS LIMIT 1;
+----------------------------------------------------------------+----------------------------------------------------------------+
|KEY                                                             |PAYLOAD                                                         |
+----------------------------------------------------------------+----------------------------------------------------------------+
|{SCHEMA={"type":"struct","fields":[{"type":"int32","optional":fa|{ID=1, USER_ID=1, PRODUCT_NAME=Product A, QUANTITY=2, ORDER_DATE|
|lse,"default":0,"field":"id"}],"optional":false,"name":"customer|=1771174557124084}                                              |
|s.public.orders.Key"}, PAYLOAD={ID=1}}                          |                                                                |
Limit Reached
Query terminated

```

**5.1.7. Теперь можно делать запросы**, в которых `key` и `payload` разложим по полям:

**NB**: в `postgresql` мы не прописали `CURRENT_TIMESTAMP(3)`,
а просто `CURRENT_TIMESTAMP`, что даёт `CURRENT_TIMESTAMP(6)`.

В `ksqldb` же `TIMESTAMP` - это `milliceconds`, не `microseconds`.
Поэтому мы `created_at` и `order_date` определили как `BIGINT`,
а к `TIMESTAMP` приведём при выборке, поделив предварительно на 1000
(в ksqldb `/` классически даёт целочисленное деление, если оба числа целые).

```bash
ksql> SELECT
>  key->payload->id as key_id,
>  payload->id,
>  FROM_UNIXTIME(payload->created_at/1000) AS created_at
>FROM
>  CDC_RAW_USERS
>LIMIT 2
>;
+--------+------+-------------------------+
|KEY_ID  |ID    |CREATED_AT               |
+--------+------+-------------------------+
|1       |1     |2026-02-15T16:55:57.122  |
|2       |2     |2026-02-15T16:55:57.122  |
Limit Reached
Query terminated

ksql> SELECT
>  key->payload->id as key_id,
>  payload->id,
>  FROM_UNIXTIME(payload->order_date/1000) AS order_date
>FROM
>  CDC_RAW_ORDERS
>LIMIT 2
>;
+--------+------+-------------------------+
|KEY_ID  |ID    |ORDER_DATE               |
+--------+------+-------------------------+
|1       |1     |2026-02-15T16:55:57.124  |
|2       |2     |2026-02-15T16:55:57.124  |
Limit Reached
Query terminated
```

**5.1.8. Я добавил одну запись в users, потом проапдейтил её, потом удалил**

```bash
customers=# insert into users (name, email) values ('Boo Moo', 'boo@moo.com');
INSERT 0 1

customers=# update users set email = 'moo@boo.com' where id = 5;
UPDATE 1

customers=# delete from users where id = 5;
DELETE 1
```

*CDC на удаление запишет в Value null, но ид удалённой записи будет в Key (вывожу только три последние записи):*

```bash
ksql> SELECT
>  key->payload->id as key_id,
>  payload->id,
>  FROM_UNIXTIME(payload->created_at/1000) AS created_at
>FROM
>  CDC_RAW_USERS
>LIMIT 20
>;
+----------+------+-------------------------+
|KEY_ID    |ID    |CREATED_AT               |
+----------+------+-------------------------+
|5         |5     |2026-02-15T20:32:19.401  |
|5         |5     |2026-02-15T20:32:19.401  |
|5         |null  |null                     |
Query Completed
Query terminated

```

**5.1.9. Итого**

Итого - CDC-сообщения можно потреблять :).


## <a name = "signal">6. Ресерч: Инкрементальные снапшоты по сигналам</a>

Для тестирования данного функционала необходимо

- перезапустить проект с ноля
- создать другой коннектор
- подать сигнал (сообщение в сигнальный топик) на инкрементальный снапшот

**NB**: таблица в рсубд для `source channel` создаётся автоматически при развёртывании проекта (см. `./postgres/init-scripts/create_tables.sql` и соотв. инструкции в `./docker-compose.yaml`).

*Автосоздание таблиц работает только если volume с данными постгреса (см. `postgres_data:/var/lib/postgresql/data` в `./docker-compose.yaml`) пуст, то есть при первом запуске проекта или запуске после `down -v`, поэтому если надо пересоздавать структуру руками - см. `./postgres/init-scripts/create_tables.sql`.*

**NB**: зачем мы вообще создали `source channel` наряду с `kafka channel` (см. ниже в конфиге коннектора настойку `"signal.enabled.channels": "source,kafka"`)?
Так повелел Debezium (и ниже мы убедимся, что он действительно что-то пишет в postgres, когда делает снапшот по согналу в kafka channel):

```
https://debezium.io/documentation/reference/stable/configuration/signalling.html

Note:

To use Kafka signaling to trigger ad hoc incremental snapshots for most connectors,
you must first enable a source signaling channel in the connector configuration.

The source channel implements a watermarking mechanism to deduplicate events
that might be captured by an incremental snapshot and then captured again
after streaming resumes.

Enabling the source channel is not required when using a signaling channel
to trigger an incremental snapshot of a read-only MySQL database that has GTIDs enabled.
For more information, see MySQL read only incremental snapshot.
```

**NB: you must first enable a source signaling channel in the connector configuration**

### <a name="signal_restart">6.1. Перезапускаем проект</a>

```bash
tesla@tesla:/.../ya_kafka_project5$ sudo docker compose --env-file .env.793 down -v
...
tesla@tesla:/.../ya_kafka_project5$ sudo docker compose --env-file .env.793 up -d --build
...
tesla@tesla:/.../ya_kafka_project5$ sudo docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Networks}}"
...
```

### <a name="signal_rdbms_ddl">6.2. Убедимся, что создалась таблица `customers.public.debezium_signal`</a>

```bash
customers=# \d public.debezium_signal

                  Table "public.debezium_signal"
 Column |          Type           | Collation | Nullable | Default 
--------+-------------------------+-----------+----------+---------
 id     | character varying(42)   |           | not null | 
 type   | character varying(32)   |           | not null | 
 data   | character varying(2048) |           |          | 
Indexes:
    "debezium_signal_pkey" PRIMARY KEY, btree (id)

```

### <a name="signal_connector">6.3. Создаём коннектор со снапшотом `no_data` и конфигурацией сигналов</a>

```bash
tesla@tesla:/.../ya_kafka_project5$ curl -sX DELETE http://localhost:8073/connectors/pg-connector | jq
{
  "error_code": 404,
  "message": "Connector pg-connector not found"
}
```

Теперь создаём уже из файла `./connector4signals.json`:

```bash
tesla@tesla:/.../ya_kafka_project5$ curl -sX POST -H 'Content-Type: application/json' --data @connector4signals.json http://localhost:8073/connectors | jq
{
  "name": "pg-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres-user",
    "database.password": "postgres-pw",
    "database.dbname": "customers",
    "table.include.list": "public.users,public.orders",
    "column.mask.with.3.chars": "public.users.email,public.users.name",
    "heartbeat.interval.ms": "30000",
    "snapshot.mode": "no_data",
    "signal.enabled.channels": "source,kafka",
    "signal.data.collection": "public.debezium_signal",
    "signal.kafka.bootstrap.servers": "localhost:9092",
    "signal.kafka.topic": "customers_signaling_topic",
    "signal.kafka.poll.timeout.ms": "100",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "topic.prefix": "customers",
    "topic.creation.enable": "true",
    "topic.creation.default.replication.factor": "-1",
    "topic.creation.default.partitions": "-1",
    "skipped.operations": "none",
    "name": "pg-connector"
  },
  "tasks": [],
  "type": "source"
}

```

Статус:

```bash
tesla@tesla:/.../ya_kafka_project5$ curl -s GET http://localhost:8073/connectors/pg-connector/status | jq
{
  "name": "pg-connector",
  "connector": {
    "state": "RUNNING",
    "worker_id": "localhost:8083"
  },
  "tasks": [
    {
      "id": 0,
      "state": "RUNNING",
      "worker_id": "localhost:8083"
    }
  ],
  "type": "source"
}

```

### <a name="signal_initial_snapshot">6.4. Убедимся, что не был сделан `initial snapshot`</a>

Идём в Rafka UI

`http://192.168.100.225:8070/ui/clusters/p5/all-topics?perPage=25`

и не видим там топики `customers.public.orders`, `customers.public.users`

### <a name="signal_topic">6.5. Создадим топик `customers_signaling_topic`</a>

`http://192.168.100.225:8070/ui/clusters/p5/all-topics/create-new-topic`

### <a name="signal_message">6.6. Отправим сигнал на создание инкрементного снапшота</a>

`http://192.168.100.225:8070/ui/clusters/p5/all-topics/customers_signaling_topic -> Produce Message`

- Key: customers
- Value: {"type":"execute-snapshot","data": {"data-collections": ["public.users", "public.orders"], "type": "INCREMENTAL"}}

### <a name="signal_logs">6.7. Смотрим в логи Kafka Connect</a>

```bash
tesla@tesla:/.../ya_kafka_project5$ sudo docker logs -n 100 yakafka-p5-kafka-connect
...
[2026-02-14 23:48:53,118] INFO Requested 'INCREMENTAL' snapshot of data collections '[public.users, public.orders]' with additional conditions '[]' and surrogate key 'PK of table will be used' (io.debezium.pipeline.signal.actions.snapshotting.ExecuteSnapshot)
...
[2026-02-14 23:48:53,265] INFO The task will send records to topic 'customers.public.debezium_signal' for the first time. Checking whether topic exists (org.apache.kafka.connect.runtime.AbstractWorkerSourceTask)
[2026-02-14 23:48:53,266] INFO Creating topic 'customers.public.debezium_signal' (org.apache.kafka.connect.runtime.AbstractWorkerSourceTask)
...
[2026-02-14 23:48:53,300] INFO The task will send records to topic 'customers.public.users' for the first time. Checking whether topic exists (org.apache.kafka.connect.runtime.AbstractWorkerSourceTask)
[2026-02-14 23:48:53,301] INFO Creating topic 'customers.public.users' (org.apache.kafka.connect.runtime.AbstractWorkerSourceTask)
...
[2026-02-14 23:48:53,615] INFO The task will send records to topic 'customers.public.orders' for the first time. Checking whether topic exists (org.apache.kafka.connect.runtime.AbstractWorkerSourceTask)
[2026-02-14 23:48:53,615] INFO Creating topic 'customers.public.orders' (org.apache.kafka.connect.runtime.AbstractWorkerSourceTask)
...
```

### <a name="signal_topics">6.8. Проверим топики в Kafka UI</a>

`http://192.168.100.225:8070/ui/clusters/p5/all-topics?perPage=25`

| Topic Name | Partitions | Out of sync replicas | Replication Factor | Number of messages | Size |
|------------|------------|----------------------|--------------------|--------------------|------|
| `customers.public.debezium_signal` | 1 | 0 | 1 | 6 | 5 KB |
| `customers.public.orders` | 1 | 0 | 1 | 5 | 5 KB |
| `customers.public.users` | 1 | 0 | 1 | 4 | 4 KB |
| `customers_signaling_topic` | 1 | 0 | 1 | 1 | 189 Bytes |

### <a name="signal_rdbms_dml">6.9. Посмотрим, что ОНО напихало в рсубд</a>

```
customers=# select * FROM public.debezium_signal;
                     id                     |         type          |                                                        data                                                         
--------------------------------------------+-----------------------+---------------------------------------------------------------------------------------------------------------------
 31f607c5-a9d8-40e5-9e8b-a854d155d4f6-open  | snapshot-window-open  | {"openWindowTimestamp": "2026-02-14T23:48:53.122565871Z"}
 31f607c5-a9d8-40e5-9e8b-a854d155d4f6-close | snapshot-window-close | {"openWindowTimestamp": "2026-02-14T23:48:53.122565871Z", "closeWindowTimestamp": "2026-02-14T23:48:53.134333452Z"}
 bf118011-0100-49c7-8825-156f13f7f006-open  | snapshot-window-open  | {"openWindowTimestamp": "2026-02-14T23:48:53.150682956Z"}
 bf118011-0100-49c7-8825-156f13f7f006-close | snapshot-window-close | {"openWindowTimestamp": "2026-02-14T23:48:53.150682956Z", "closeWindowTimestamp": "2026-02-14T23:48:53.159537984Z"}
 b3b11299-ace5-492f-a144-7d72aeb74911-open  | snapshot-window-open  | {"openWindowTimestamp": "2026-02-14T23:48:53.164146458Z"}
 b3b11299-ace5-492f-a144-7d72aeb74911-close | snapshot-window-close | {"openWindowTimestamp": "2026-02-14T23:48:53.164146458Z", "closeWindowTimestamp": "2026-02-14T23:48:53.165837850Z"}
(6 rows)
```

### <a name="signal_summary">6.10. Итого</a>

**Итого - Вроде как бы у нас получилось: мы сделали инкрементный снапшот по сигналу в кафка-топик.**