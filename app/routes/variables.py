# app/routes/variables.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app import crud, schemas, database
import os, secrets

security = HTTPBasic()
router = APIRouter(prefix="/enviroments", tags=["Variables"])


API_USER = os.getenv("API_USER", "admin")
API_PASSWORD = os.getenv("API_PASSWORD", "supersecrettoken")

def authenticate(credentials: HTTPBasicCredentials):
    """Autentica usando credenciales del entorno (.env)"""
    if not (
        secrets.compare_digest(credentials.username, API_USER)
        and secrets.compare_digest(credentials.password, API_PASSWORD)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )


@router.get("/{env_name}/variables", response_model=schemas.PaginatedResponse)
def list_variables(
    env_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: Session = Depends(database.get_db)
):
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise HTTPException(status_code=404, detail="Entorno no encontrado")

    variables, count = crud.get_variables_by_env(db, env_name, skip, limit)
    response = schemas.PaginatedResponse(
        count=count,
        next=f"/enviroments/{env_name}/variables?page={(skip//limit)+2}" if (skip+limit) < count else None,
        previous=f"/enviroments/{env_name}/variables?page={(skip//limit)}" if skip > 0 else None,
        results=variables
    )
    return response


@router.post("/{env_name}/variables", response_model=schemas.VariableOut, status_code=201)
def create_variable(
    env_name: str,
    var: schemas.VariableCreate,
    db: Session = Depends(database.get_db),
    credentials: HTTPBasicCredentials = Depends(security)
):
    authenticate(credentials)
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise HTTPException(status_code=404, detail="Entorno no encontrado")

    existing = crud.get_variable_by_name(db, env_name, var.name)
    if existing:
        raise HTTPException(status_code=400, detail="Variable ya existente")

    return crud.create_variable(db, env_name, var)


@router.get("/{env_name}/variables/{var_name}", response_model=schemas.VariableOut)
def get_variable(env_name: str, var_name: str, db: Session = Depends(database.get_db)):
    variable = crud.get_variable_by_name(db, env_name, var_name)
    if not variable:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    return variable


@router.put("/{env_name}/variables/{var_name}", response_model=schemas.VariableOut)
def update_variable_full(
    env_name: str,
    var_name: str,
    var_update: schemas.VariableBase,
    db: Session = Depends(database.get_db),
    credentials: HTTPBasicCredentials = Depends(security)
):
    authenticate(credentials)
    db_var = crud.get_variable_by_name(db, env_name, var_name)
    if not db_var:
        raise HTTPException(status_code=404, detail="Variable no encontrada")

    return crud.update_variable(db, db_var, var_update, partial=False)


@router.patch("/{env_name}/variables/{var_name}", response_model=schemas.VariableOut)
def update_variable_partial(
    env_name: str,
    var_name: str,
    var_update: schemas.VariableBase,
    db: Session = Depends(database.get_db),
    credentials: HTTPBasicCredentials = Depends(security)
):
    authenticate(credentials)
    db_var = crud.get_variable_by_name(db, env_name, var_name)
    if not db_var:
        raise HTTPException(status_code=404, detail="Variable no encontrada")

    return crud.update_variable(db, db_var, var_update, partial=True)


@router.delete("/{env_name}/variables/{var_name}", status_code=204)
def delete_variable(
    env_name: str,
    var_name: str,
    db: Session = Depends(database.get_db),
    credentials: HTTPBasicCredentials = Depends(security)
):
    authenticate(credentials)
    db_var = crud.get_variable_by_name(db, env_name, var_name)
    if not db_var:
        raise HTTPException(status_code=404, detail="Variable no encontrada")

    crud.delete_variable(db, db_var)
    return
