# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Esquemas de Base y Tiempos ---
class TimestampModel(BaseModel):
    created_at: datetime
    updated_at: datetime
    
    class Config:
        # Permite que Pydantic lea los datos del objeto SQLAlchemy
        from_attributes = True 

# --- Entornos ---
class EnvironmentBase(BaseModel):
    name: str = Field(..., example="staging", description="Nombre único del entorno")
    description: Optional[str] = None

class EnvironmentCreate(EnvironmentBase):
    pass # Usado para POST (creación)

class EnvironmentUpdate(BaseModel):
    # Usado para PATCH: los campos son opcionales
    description: Optional[str] = None
    
class EnvironmentOut(EnvironmentBase, TimestampModel):
    pass # Usado para GET/PUT/PATCH (respuesta)

# --- Variables ---
class VariableBase(BaseModel):
    name: str = Field(..., example="DB_URL", description="Nombre único de la variable")
    value: str
    description: Optional[str] = None
    is_sensitive: Optional[bool] = False

class VariableCreate(VariableBase):
    pass # Usado para POST (creación)

class VariableOut(VariableBase, TimestampModel):
    env_name: str # Incluimos el nombre del entorno en la respuesta

# --- Esquema de Respuesta Paginada (Requisito D) ---
class PaginatedResponse(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List # La lista contendrá EnvironmentOut o VariableOut