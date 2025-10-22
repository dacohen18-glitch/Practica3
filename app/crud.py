# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from typing import List, Tuple, Dict, Optional

# --- CRUD de Entornos (Environments) ---

def create_environment(db: Session, env: schemas.EnvironmentCreate) -> models.Environment:
    # Lógica de creación (POST /enviroments/)
    db_env = models.Environment(**env.model_dump())
    db.add(db_env)
    db.commit()
    db.refresh(db_env)
    return db_env

def get_environment_by_name(db: Session, env_name: str) -> Optional[models.Environment]:
    # Lógica de obtención por nombre (GET /enviroments/{name}/)
    return db.query(models.Environment).filter(models.Environment.name == env_name).first()

def get_environments(db: Session, skip: int = 0, limit: int = 10) -> Tuple[List[models.Environment], int]:
    # Lógica de listado y paginación (GET /enviroments/)
    count = db.query(models.Environment).count()
    environments = db.query(models.Environment).offset(skip).limit(limit).all()
    return environments, count

def update_environment(db: Session, db_env: models.Environment, env_update: schemas.EnvironmentUpdate) -> models.Environment:
    # Lógica de actualización (PUT/PATCH /enviroments/{name}/)
    # Solo permitimos actualizar la descripción según el esquema
    if env_update.description is not None:
        db_env.description = env_update.description
    
    db.add(db_env)
    db.commit()
    db.refresh(db_env)
    return db_env

def delete_environment(db: Session, db_env: models.Environment):
    # Lógica de eliminación (DELETE /enviroments/{name}/)
    db.delete(db_env)
    db.commit()

# --- CRUD de Variables (Variables) ---

def create_variable(db: Session, env_name: str, var: schemas.VariableCreate) -> models.Variable:
    # Lógica de creación (POST /variables/)
    db_var = models.Variable(**var.model_dump(), env_name=env_name)
    db.add(db_var)
    db.commit()
    db.refresh(db_var)
    return db_var

def get_variable_by_name(db: Session, env_name: str, var_name: str) -> Optional[models.Variable]:
    # Lógica de obtención por nombre (GET /variables/{name})
    return db.query(models.Variable).filter(
        models.Variable.env_name == env_name, 
        models.Variable.name == var_name
    ).first()

def get_variables_by_env(db: Session, env_name: str, skip: int = 0, limit: int = 10) -> Tuple[List[models.Variable], int]:
    # Lógica de listado y paginación (GET /variables/)
    query = db.query(models.Variable).filter(models.Variable.env_name == env_name)
    count = query.count()
    variables = query.offset(skip).limit(limit).all()
    return variables, count

def update_variable(db: Session, db_var: models.Variable, var_update: schemas.VariableBase, partial: bool = False) -> models.Variable:
    # Lógica de actualización (PUT/PATCH /variables/{name}). Maneja actualización parcial (PATCH)
    update_data = var_update.model_dump(exclude_unset=partial) 
    
    for key, value in update_data.items():
        setattr(db_var, key, value)
    
    db.add(db_var)
    db.commit()
    db.refresh(db_var)
    return db_var

def delete_variable(db: Session, db_var: models.Variable):
    # Lógica de eliminación (DELETE /variables/{name})
    db.delete(db_var)
    db.commit()

# --- Función de Consumo Masivo ---

def get_config_json_for_env(db: Session, env_name: str) -> Dict[str, str]:
    # Lógica para GET /{env_name}.json
    variables = db.query(models.Variable).filter(models.Variable.env_name == env_name).all()
    
    # Requisito E: devolver JSON plano (diccionario {nombre: valor})
    config_dict = {var.name: var.value for var in variables}
    return config_dict