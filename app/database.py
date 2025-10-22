# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from .models import Base 
# Para desarrollo local si no se usa docker-compose (opcional, pero buena práctica)
from dotenv import load_dotenv

load_dotenv() 

# La URL de la DB se toma de las variables de entorno. 
# En Docker, será "postgresql://user:pass@database:5432/configdb"
DATABASE_URL = os.environ.get("DATABASE_URL") 

# Si no está en el entorno (por ejemplo, en pruebas locales sin Docker Compose)
if not DATABASE_URL:
    DB_USER = os.environ.get("POSTGRES_USER", "appuser")
    DB_PASS = os.environ.get("POSTGRES_PASSWORD", "passwordsegura123")
    DB_NAME = os.environ.get("POSTGRES_DB", "configdb")
    # Usa 'localhost' para el desarrollo sin Docker o 'database' con Docker Compose
    DB_HOST = os.environ.get("DB_HOST", "localhost") 
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}" 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependencia de FastAPI para obtener una sesión de DB."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_tables():
    """Crea las tablas definidas en models.py si no existen."""
    Base.metadata.create_all(bind=engine)