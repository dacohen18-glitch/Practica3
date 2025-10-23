# conftest.py
import pytest
import os

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Configura variables de entorno para tests."""
    os.environ["API_USER"] = "test_user"
    os.environ["API_PASSWORD"] = "test_password"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    yield

@pytest.fixture
def sample_environment_data():
    """Fixture con datos de ejemplo para entornos."""
    return {
        "name": "staging",
        "description": "Entorno de staging para pruebas"
    }

@pytest.fixture
def sample_variable_data():
    """Fixture con datos de ejemplo para variables."""
    return {
        "name": "API_KEY",
        "value": "test_api_key_12345",
        "description": "API key para servicios externos",
        "is_sensitive": True
    }

