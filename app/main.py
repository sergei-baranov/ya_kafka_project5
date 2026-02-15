import logging

from ksql import KSQLAPI


logging.basicConfig(level=logging.DEBUG)
client = KSQLAPI('http://ksqldb-server:8088')

def print_cdc_records(limit: int = 5):
    ...

if __name__ == "__main__":
    print_cdc_records()
