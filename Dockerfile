# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para PostgreSQL (psycopg2)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    curl \
    libpq-dev \
    && rm -rf /var/cache/apt/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . /app

# Exponer puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/status/ || exit 1

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]