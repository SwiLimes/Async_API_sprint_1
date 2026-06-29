import time
from elasticsearch import Elasticsearch
from functional.settings import test_settings

if __name__ == "__main__":
    host = test_settings.es_host
    port = test_settings.es_port
    es_client = Elasticsearch(f'http://{host}:{port}')
    while True:
        if es_client.ping():
            break
        time.sleep(1)