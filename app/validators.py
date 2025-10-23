# app/validators.py
from pydantic import field_validator
from app.utils import is_valid_slug, validate_environment_name, validate_variable_name

class SlugValidator:
    """Mixin para validar campos que deben ser slugs."""
    
    @field_validator('name')
    @classmethod
    def validate_slug_format(cls, v: str) -> str:
        """Valida que el nombre sea un slug válido."""
        if not is_valid_slug(v):
            raise ValueError(
                'El nombre debe ser un URL slug válido '
                '(solo letras minúsculas, números y guiones)'
            )
        return v.lower()

class EnvironmentNameValidator:
    """Mixin para validar nombres de entornos."""
    
    @field_validator('name')
    @classmethod
    def validate_environment_name(cls, v: str) -> str:
        """Valida el nombre del entorno."""
        is_valid, error_msg = validate_environment_name(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v

class VariableNameValidator:
    """Mixin para validar nombres de variables."""
    
    @field_validator('name')
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        """Valida el nombre de la variable."""
        is_valid, error_msg = validate_variable_name(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v.upper()  # Convertir a mayúsculas automáticamente

class VariableValueValidator:
    """Mixin para validar valores de variables."""
    
    @field_validator('value')
    @classmethod
    def validate_value_length(cls, v: str) -> str:
        """Valida que el valor no exceda un límite razonable."""
        max_length = 5000  # 5KB aproximadamente
        if len(v) > max_length:
            raise ValueError(f'El valor no puede exceder {max_length} caracteres')
        return v