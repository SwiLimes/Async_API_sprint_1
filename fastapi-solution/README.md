# Кинотеатр

## Docker

```bash
cd fastapi-solution
cp .env.exemple .env
docker compose up --build -d
```

Остановить все контейнеры:
```bash
docker stop $(docker ps -q)
```
Удалить все контейнеры:
```bash
docker container prune -f 
```
Просмотреть статус всех имеющихся контейнеров:
```bash
docker ps -a
```
Просмотреть логи основного контейнера:
```bash
docker logs api-service
```

## Ручной запуск

```bash
cd fastapi-solution
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Swagger

[Swagger UI](http://localhost:8000/api/openapi)

### ETL state

Убрать отметки о наибольшей дате записей, для которых обновлён индекс в ElasticSearch:
```bash
cd fastapi-solution
echo '{}' > src/etl/state/state.json
```