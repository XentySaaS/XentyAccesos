# Runtime fijado a 3.12 (matriz de soporte de Django 5.0.6). Independiente del Python local.
# Para subir a 3.13/3.14 hay que cambiar también la versión de Django (decisión de stack).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libmagic1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
