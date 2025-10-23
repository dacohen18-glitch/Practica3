# app/utils.py
import re
from typing import Optional
from datetime import datetime

def is_valid_slug(value: str) -> bool:
    """
    Valida que un string sea un URL slug válido.
    Permite: letras minúsculas, números, guiones y guiones bajos.
    """
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    return bool(re.match(pattern, value.lower()))

def slugify(value: str) -> str:
    """
    Convierte un string en un URL slug válido.
    Ejemplo: "My Environment" -> "my-environment"
    """
    value = value.lower().strip()
    value = re.sub(r'[^\w\s-]', '', value)
    value = re.sub(r'[-\s]+', '-', value)
    return value

def mask_sensitive_value(value: str, show_chars: int = 4) -> str:
    """
    Enmascara un valor sensible, mostrando solo los primeros N caracteres.
    Ejemplo: "supersecret123" -> "supe**********"
    """
    if len(value) <= show_chars:
        return '*' * len(value)
    return value[:show_chars] + '*' * (len(value) - show_chars)

def format_datetime_iso(dt: Optional[datetime]) -> Optional[str]:
    """
    Formatea un datetime a string ISO 8601.
    """
    if dt is None:
        return None
    return dt.isoformat()

def validate_environment_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Valida el nombre de un entorno según las reglas de negocio.
    Retorna: (es_válido, mensaje_error)
    """
    if not name:
        return False, "El nombre no puede estar vacío"
    
    if len(name) > 50:
        return False, "El nombre no puede exceder 50 caracteres"
    
    if not is_valid_slug(name):
        return False, "El nombre debe ser un URL slug válido (solo letras minúsculas, números y guiones)"
    
    return True, None

def validate_variable_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Valida el nombre de una variable según las reglas de negocio.
    Retorna: (es_válido, mensaje_error)
    """
    if not name:
        return False, "El nombre no puede estar vacío"
    
    if len(name) > 100:
        return False, "El nombre no puede exceder 100 caracteres"
    
    # Variables suelen usar UPPER_CASE_SNAKE_CASE
    pattern = r'^[A-Z0-9_]+$'
    if not re.match(pattern, name):
        return False, "El nombre debe usar el formato UPPER_SNAKE_CASE (ej: DB_URL, API_KEY)"
    
    return True, None

def parse_boolean_string(value: str) -> bool:
    """
    Convierte strings comunes de boolean a bool.
    Acepta: true/false, yes/no, 1/0 (case insensitive)
    """
    true_values = {'true', 'yes', '1', 'on'}
    false_values = {'false', 'no', '0', 'off'}
    
    value_lower = value.lower().strip()
    
    if value_lower in true_values:
        return True
    elif value_lower in false_values:
        return False
    else:
        raise ValueError(f"No se puede convertir '{value}' a boolean")

def calculate_pagination_metadata(total: int, page: int, size: int) -> dict:
    """
    Calcula metadatos de paginación.
    Retorna: dict con total_pages, has_next, has_previous
    """
    total_pages = (total + size - 1) // size  # Redondeo hacia arriba
    
    return {
        "total_pages": total_pages,
        "current_page": page,
        "page_size": size,
        "total_items": total,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }