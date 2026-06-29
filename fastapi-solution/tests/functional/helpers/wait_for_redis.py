import time
import redis
from functional.settings import test_settings

if __name__ == '__main__':
    host = test_settings.redis_host
    port = test_settings.redis_port
    redis_client = redis.Redis(host=host, port=port)

    while True:
        if redis_client.ping():
            break

        time.sleep(1)
