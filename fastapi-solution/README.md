# Кинотеатр

## Docker

```bash
cd fastapi-solution
cp .env.exemple .env
docker compose up --build
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
