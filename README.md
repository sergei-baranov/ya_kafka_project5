- разворачиваем ансамбль
- убеждаемся, что таблицы созданы и заполнены
- создаём коннектор
- видим в юи кафки, что тот сделал инишл снашот (сообщения в 2 топика)
- смотрим вообще по разным урл-ам
- даём нагрузку на постгрес
- смотрим в графану
- смотрим в топик
- запускаем питонячье приложение, которое даёт нагрузку и читает три топика (хертбит, юзерз, ордерз) - например просто кол-во сообщений и последние 5 - до и после нагрузки, или только после... или по командам, тогда на Фаусте



```bash
# PUT и PATCH - not allowed, соотв. юзаем DELETE + POST на коллекцию,
# или PUT на ресурс

tesla@tesla:/media/tesla/NETAC_4T/VCS/ya_kafka_415$ curl -sX DELETE http://localhost:8073/connectors/pg-connector | jq

tesla@tesla:/media/tesla/NETAC_4T/VCS/ya_kafka_415$ curl -sX DELETE http://localhost:8073/connectors/pg-connector | jq
{
  "error_code": 404,
  "message": "Connector pg-connector not found"
}

tesla@tesla:/media/tesla/NETAC_4T/VCS/ya_kafka_415$ curl -sX POST -H 'Content-Type: application/json' --data @connector.json http://localhost:8073/connectors | jq

```
