# app/exceptions.py
from fastapi import HTTPException, status

class EnvironmentNotFoundException(HTTPException):
    """Excepción cuando no se encuentra un entorno."""
    def __init__(self, env_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entorno '{env_name}' no encontrado"
        )

class EnvironmentAlreadyExistsException(HTTPException):
    """Excepción cuando se intenta crear un entorno duplicado."""
    def __init__(self, env_name: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El entorno '{env_name}' ya existe"
        )

class VariableNotFoundException(HTTPException):
    """Excepción cuando no se encuentra una variable."""
    def __init__(self, var_name: str, env_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Variable '{var_name}' no encontrada en entorno '{env_name}'"
        )

class VariableAlreadyExistsException(HTTPException):
    """Excepción cuando se intenta crear una variable duplicada."""
    def __init__(self, var_name: str, env_name: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La variable '{var_name}' ya existe en el entorno '{env_name}'"
        )

class InvalidCredentialsException(HTTPException):
    """Excepción para credenciales inválidas."""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"}
        )

class DatabaseConnectionException(HTTPException):
    """Excepción para errores de conexión a base de datos."""
    def __init__(self, detail: str = "Error de conexión a la base de datos"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )

class InvalidSlugException(HTTPException):
    """Excepción para nombres que no son slugs válidos."""
    def __init__(self, field_name: str, value: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} '{value}' no es un slug válido. Use solo letras minúsculas, números y guiones."
        )