import asyncio

import nest_asyncio
from ksqldb import KSQLdbClient


async def main():
    client = KSQLdbClient('http://ksqldb-server:8088')
    stream_properties = {"ksql.streams.auto.offset.reset": "earliest"}

    client.ksql("DROP STREAM IF EXISTS cdc_raw_orders;")
    client.ksql("DROP STREAM IF EXISTS cdc_raw_users;")
    client.ksql("""
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
    """)
    client.ksql("""
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
""")

    query = "SELECT KEY, PAYLOAD FROM CDC_RAW_USERS LIMIT 1;"
    print(f'\n\nquery_sync: {query}:\n')
    results = client.query_sync(query, timeout=None)
    for row in results:
        print(row)

    query = "SELECT KEY, PAYLOAD FROM CDC_RAW_ORDERS LIMIT 1;"
    print(f'\n\nquery_sync: {query}:\n')
    results = client.query_sync(query, timeout=None)
    for row in results:
        print(row)

    query = """
SELECT
  key->payload->id as key_id,
  payload->id,
  FROM_UNIXTIME(payload->created_at/1000) AS created_at
FROM
  CDC_RAW_USERS
LIMIT 2
;
"""
    print(f'\n\nquery_sync: {query}:\n')
    results = client.query_sync(query, timeout=None)
    for row in results:
        print(row)

    query = """
SELECT
  key->payload->id as key_id,
  payload->id,
  FROM_UNIXTIME(payload->order_date/1000) AS order_date
FROM
  CDC_RAW_ORDERS
LIMIT 2
;
"""
    print(f'\n\nquery_async: {query}:\n')
    # query_async
    query_id = None
    async for row in client.query_async(
            query,
            stream_properties=stream_properties,
            timeout=None
    ):
        if isinstance(row, dict) and 'queryId' in row:
            query_id = row['queryId']
        print(row)
    if query_id:
        client.close_query(query_id)


if __name__ == "__main__":
    current_loop = asyncio.get_event_loop()
    nest_asyncio.apply(current_loop)
    asyncio.run(main())
