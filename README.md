# Config Service API 🧩
Servicio RESTful para la gestión dinámica de entornos y variables de configuración.

## Ejecución con Docker Compose
1. Clonar el repositorio
2. Crear archivo `.env` con las variables de entorno
    "POSTGRES_USER=appuser
    POSTGRES_PASSWORD=passwordsegura123
    POSTGRES_DB=configdb
    API_USER=admin
    API_PASSWORD=supersecrettoken"
3. Ejecutar:
   docker compose up --build

## Ejecutar Tests
1. Ejecutar:
    pip install -r requirements-dev.txt
2. Ejecutar: 
    pytest app/tests.py -v

