# app/tests.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import base64

from main import app, authenticate_user
from app.database import Base, get_db
from app import models

# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override de la dependencia de DB para tests."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_auth():
    """Override de autenticación para tests."""
    return "test_user"

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[authenticate_user] = override_auth

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """Crea las tablas antes de cada test y las elimina después."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def get_basic_auth_header(username: str = "admin", password: str = "supersecrettoken"):
    """Genera el header de autenticación básica."""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

# ===== TESTS DE HEALTH CHECK =====
def test_health_check():
    """Test del endpoint /status/"""
    response = client.get("/status/")
    assert response.status_code == 200
    assert response.json() == {"status": "pong"}

# ===== TESTS DE ENTORNOS =====
def test_create_environment():
    """Test de creación de entorno."""
    response = client.post(
        "/enviroments/",
        json={"name": "production", "description": "Entorno de producción"},
        headers=get_basic_auth_header()
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "production"
    assert data["description"] == "Entorno de producción"
    assert "created_at" in data
    assert "updated_at" in data

def test_create_duplicate_environment():
    """Test de error al crear entorno duplicado."""
    client.post(
        "/enviroments/",
        json={"name": "staging", "description": "Staging"},
        headers=get_basic_auth_header()
    )
    response = client.post(
        "/enviroments/",
        json={"name": "staging", "description": "Duplicado"},
        headers=get_basic_auth_header()
    )
    assert response.status_code == 400
    assert "ya existe" in response.json()["detail"]

def test_get_environment():
    """Test de obtención de un entorno específico."""
    client.post(
        "/enviroments/",
        json={"name": "development", "description": "Dev"},
        headers=get_basic_auth_header()
    )
    response = client.get("/enviroments/development/", headers=get_basic_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "development"

def test_get_nonexistent_environment():
    """Test de error 404 al buscar entorno inexistente."""
    response = client.get("/enviroments/nonexistent/", headers=get_basic_auth_header())
    assert response.status_code == 404

def test_list_environments_pagination():
    """Test de listado paginado de entornos."""
    # Crear varios entornos
    for i in range(15):
        client.post(
            "/enviroments/",
            json={"name": f"env{i}", "description": f"Environment {i}"},
            headers=get_basic_auth_header()
        )
    
    response = client.get("/enviroments/?page=1&size=10", headers=get_basic_auth_header())
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 15
    assert len(data["results"]) == 10
    assert data["next"] is not None
    assert data["previous"] is None

def test_update_environment():
    """Test de actualización de entorno (PUT/PATCH)."""
    client.post(
        "/enviroments/",
        json={"name": "testing", "description": "Initial"},
        headers=get_basic_auth_header()
    )
    response = client.put(
        "/enviroments/testing/",
        json={"description": "Updated description"},
        headers=get_basic_auth_header()
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"

def test_delete_environment():
    """Test de eliminación de entorno."""
    client.post(
        "/enviroments/",
        json={"name": "todelete", "description": "Will be deleted"},
        headers=get_basic_auth_header()
    )
    response = client.delete("/enviroments/todelete/", headers=get_basic_auth_header())
    assert response.status_code == 204
    
    # Verificar que ya no existe
    response = client.get("/enviroments/todelete/", headers=get_basic_auth_header())
    assert response.status_code == 404

# ===== TESTS DE VARIABLES =====
def test_create_variable():
    """Test de creación de variable."""
    client.post(
        "/enviroments/",
        json={"name": "prod", "description": "Production"},
        headers=get_basic_auth_header()
    )
    response = client.post(
        "/enviroments/prod/variables",
        json={
            "name": "DB_URL",
            "value": "postgres://localhost/db",
            "description": "Database URL",
            "is_sensitive": True
        },
        headers=get_basic_auth_header()
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "DB_URL"
    assert data["value"] == "postgres://localhost/db"
    assert data["is_sensitive"] is True

def test_create_variable_nonexistent_env():
    """Test de error al crear variable en entorno inexistente."""
    response = client.post(
        "/enviroments/nonexistent/variables",
        json={"name": "VAR", "value": "value"},
        headers=get_basic_auth_header()
    )
    assert response.status_code == 404

def test_get_variable():
    """Test de obtención de variable específica."""
    client.post(
        "/enviroments/",
        json={"name": "test", "description": "Test"},
        headers=get_basic_auth_header()
    )
    client.post(
        "/enviroments/test/variables",
        json={"name": "API_KEY", "value": "secret123"},
        headers=get_basic_auth_header()
    )
    response = client.get(
        "/enviroments/test/variables/API_KEY",
        headers=get_basic_auth_header()
    )
    assert response.status_code == 200
    assert response.json()["name"] == "API_KEY"

def test_list_variables_pagination():
    """Test de listado paginado de variables."""
    client.post(
        "/enviroments/",
        json={"name": "env1", "description": "Env"},
        headers=get_basic_auth_header()
    )
    
    # Crear múltiples variables
    for i in range(12):
        client.post(
            "/enviroments/env1/variables",
            json={"name": f"VAR{i}", "value": f"value{i}"},
            headers=get_basic_auth_header()
        )
    
    response = client.get(
        "/enviroments/env1/variables?page=1&size=10",
        headers=get_basic_auth_header()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 12
    assert len(data["results"]) == 10

def test_delete_variable():
    """Test de eliminación de variable."""
    client.post(
        "/enviroments/",
        json={"name": "env3", "description": "Env"},
        headers=get_basic_auth_header()
    )
    client.post(
        "/enviroments/env3/variables",
        json={"name": "TEMP", "value": "temp"},
        headers=get_basic_auth_header()
    )
    
    response = client.delete(
        "/enviroments/env3/variables/TEMP",
        headers=get_basic_auth_header()
    )
    assert response.status_code == 204

# ===== TESTS DE CONSUMO MASIVO =====
def test_get_environment_config_json():
    """Test del endpoint de consumo masivo (.json)."""
    client.post(
        "/enviroments/",
        json={"name": "production", "description": "Prod"},
        headers=get_basic_auth_header()
    )
    client.post(
        "/enviroments/production/variables",
        json={"name": "DB_URL", "value": "postgres://prod/db"},
        headers=get_basic_auth_header()
    )
    client.post(
        "/enviroments/production/variables",
        json={"name": "API_TIMEOUT", "value": "5000"},
        headers=get_basic_auth_header()
    )
    
    response = client.get("/enviroments/production.json")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "DB_URL": "postgres://prod/db",
        "API_TIMEOUT": "5000"
    }

def test_get_config_json_nonexistent_env():
    """Test de error 404 en consumo masivo de entorno inexistente."""
    response = client.get("/enviroments/nonexistent.json")
    assert response.status_code == 404

# ===== TESTS DE OPENAPI =====
def test_openapi_schema_available():
    """Test de disponibilidad del esquema OpenAPI."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "Config Service API"