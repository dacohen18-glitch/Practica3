# main.py
from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import urllib.parse # Para construir URLs de paginación

 
from app import schemas, crud # Asume que models está importado en crud y database
from app.database import get_db, create_db_tables 

# --- Inicialización de la DB ---
# Crea las tablas al iniciar la aplicación (solo si no existen)
try:
    create_db_tables() 
except Exception as e:
    # Manejo de errores de conexión inicial (ej: la DB no está lista)
    print(f"ERROR AL CONECTAR/CREAR TABLAS: {e}")

# --- Configuración de Seguridad (Requisito G: Basic Auth) ---
API_USERNAME = os.environ.get("API_USER", "admin")
API_PASSWORD = os.environ.get("API_PASSWORD", "supersecrettoken")

security = HTTPBasic()

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Verifica las credenciales del usuario."""
    if credentials.username != API_USERNAME or credentials.password != API_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- Inicialización de FastAPI (Requisito F: OpenAPI/Swagger en /docs) ---
app = FastAPI(
    title="Config Service API",
    description="Servicio de Gestión de Configuración Dinámica.",
    version="1.0.0",
)

# ----------------------------------------------------------------------
# --- Funciones Auxiliares ---
# ----------------------------------------------------------------------

def _get_pagination_urls(request: Request, count: int, page: int, size: int, endpoint_name: str, env_name: Optional[str] = None):
    """Construye las URLs 'next' y 'previous' para la respuesta paginada."""
    
    # 1. Determinar el path base
    path = request.url_for(endpoint_name)
    if env_name:
        path = request.url_for(endpoint_name, env_name=env_name)

    # 2. Construir URLs
    next_url = None
    if (page * size) < count:
        # Usa urllib.parse.urljoin para manejar baseURL dinámicamente
        next_url = urllib.parse.urljoin(str(request.base_url), f"{path}?page={page + 1}&size={size}")
        
    previous_url = None
    if page > 1:
        previous_url = urllib.parse.urljoin(str(request.base_url), f"{path}?page={page - 1}&size={size}")
        
    return next_url, previous_url

# ----------------------------------------------------------------------
# --- Endpoints Generales ---
# ----------------------------------------------------------------------

@app.get("/status/", tags=["Salud"], summary="Health Check")
def health_check():
    """Requisito: GET /status/ (Responde pong)."""
    return {"message": "pong"}

# ----------------------------------------------------------------------
# --- Endpoints de Entornos (/enviroments) ---
# ----------------------------------------------------------------------

@app.get("/enviroments/", response_model=schemas.PaginatedResponse, tags=["Entornos"], summary="Listar Entornos (Paginado)")
def list_environments(
    request: Request,
    db: Session = Depends(get_db), 
    page: int = Query(1, ge=1), 
    size: int = Query(10, ge=1, le=100),
    user: str = Depends(authenticate_user) # Autenticación
):
    """Requisito: GET /enviroments/ (Paginado - Requisito D)."""
    skip = (page - 1) * size
    environments, count = crud.get_environments(db, skip=skip, limit=size)
    
    next_url, previous_url = _get_pagination_urls(request, count, page, size, 'list_environments')
    
    return {
        "count": count,
        "next": next_url,
        "previous": previous_url,
        "results": [schemas.EnvironmentOut.model_validate(e) for e in environments]
    }

@app.post("/enviroments/", status_code=status.HTTP_201_CREATED, tags=["Entornos"], response_model=schemas.EnvironmentOut)
def create_environment(env_in: schemas.EnvironmentCreate, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: POST /enviroments/ (Crear - Código 201)."""
    if crud.get_environment_by_name(db, env_in.name):
        # Requisito F: 400 Bad Request si el recurso ya existe
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El entorno '{env_in.name}' ya existe.")
    
    return crud.create_environment(db, env_in)

@app.get("/enviroments/{env_name}/", response_model=schemas.EnvironmentOut, tags=["Entornos"], summary="Obtener Detalle de un Entorno")
def get_environment_details(env_name: str, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: GET /enviroments/{env_name}/."""
    db_env = crud.get_environment_by_name(db, env_name)
    if db_env is None:
        # Requisito F: 404 Not Found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entorno no encontrado")
    return db_env

@app.put("/enviroments/{env_name}/", response_model=schemas.EnvironmentOut, tags=["Entornos"], summary="Actualizar COMPLETAMENTE un Entorno")
def update_environment_full(env_name: str, env_update: schemas.EnvironmentCreate, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: PUT /enviroments/{env_name}/ (Actualización completa)."""
    db_env = crud.get_environment_by_name(db, env_name)
    if db_env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entorno no encontrado")
        
    # PUT exige un cuerpo completo. Para el entorno, solo podemos cambiar la descripción.
    # Usamos el esquema de actualización para asegurar que solo se actualice la descripción.
    return crud.update_environment(db, db_env, schemas.EnvironmentUpdate(description=env_update.description))

@app.patch("/enviroments/{env_name}/", response_model=schemas.EnvironmentOut, tags=["Entornos"], summary="Actualizar PARCIALMENTE un Entorno")
def update_environment_partial(env_name: str, env_update: schemas.EnvironmentUpdate, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: PATCH /enviroments/{env_name}/ (Actualización parcial)."""
    db_env = crud.get_environment_by_name(db, env_name)
    if db_env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entorno no encontrado")
        
    # PATCH permite que la descripción sea None si no se envía
    return crud.update_environment(db, db_env, env_update)


@app.delete("/enviroments/{env_name}/", status_code=status.HTTP_204_NO_CONTENT, tags=["Entornos"], summary="Eliminar un Entorno")
def delete_environment_resource(env_name: str, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: DELETE /enviroments/{env_name}/ (Código 204)."""
    db_env = crud.get_environment_by_name(db, env_name)
    if db_env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entorno no encontrado")
        
    crud.delete_environment(db, db_env)
    return 

# ----------------------------------------------------------------------
# --- Endpoint de Consumo Masivo (Requisito E) ---
# ----------------------------------------------------------------------

@app.get("/enviroments/{env_name}.json", tags=["Consumo Masivo"], summary="Obtener Configuración JSON Plana")
def get_environment_config_json(env_name: str, db: Session = Depends(get_db)):
    """Requisito: GET /enviroments/{env_name}.json. Devuelve JSON plano."""
    db_env = crud.get_environment_by_name(db, env_name)
    if db_env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entorno no encontrado")

    config_json = crud.get_config_json_for_env(db, env_name)

    # Requisito E: devolver un objeto JSON plano (Diccionario de Python)
    return JSONResponse(content=config_json)

# ----------------------------------------------------------------------
# --- Endpoints de Variables (/enviroments/{env_name}/variables) ---
# ----------------------------------------------------------------------

@app.get("/enviroments/{env_name}/variables", response_model=schemas.PaginatedResponse, tags=["Variables"], summary="Listar Variables de un Entorno (Paginado)")
def list_variables(
    request: Request,
    env_name: str, 
    db: Session = Depends(get_db), 
    page: int = Query(1, ge=1), 
    size: int = Query(10, ge=1, le=100),
    user: str = Depends(authenticate_user)
):
    """Requisito: GET /enviroments/{env_name}/variables (Paginado)."""
    db_env = crud.get_environment_by_name(db, env_name)
    if db_env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entorno no encontrado")
        
    skip = (page - 1) * size
    variables, count = crud.get_variables_by_env(db, env_name, skip=skip, limit=size)

    # El nombre de la función aquí es 'list_variables'
    next_url, previous_url = _get_pagination_urls(request, count, page, size, 'list_variables', env_name=env_name)

    return {
        "count": count,
        "next": next_url,
        "previous": previous_url,
        "results": [schemas.VariableOut.model_validate(v) for v in variables]
    }

@app.post("/enviroments/{env_name}/variables", status_code=status.HTTP_201_CREATED, tags=["Variables"], response_model=schemas.VariableOut)
def create_variable(env_name: str, var_in: schemas.VariableCreate, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: POST /enviroments/{env_name}/variables (Crear - Código 201)."""
    db_env = crud.get_environment_by_name(db, env_name)
    if db_env is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entorno padre no encontrado.")
    
    if crud.get_variable_by_name(db, env_name, var_in.name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La variable ya existe en este entorno.")
        
    return crud.create_variable(db, env_name, var_in)

@app.get("/enviroments/{env_name}/variables/{var_name}", response_model=schemas.VariableOut, tags=["Variables"], summary="Obtener Detalle de una Variable")
def get_variable_details(env_name: str, var_name: str, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: GET /enviroments/{env_name}/variables/{var_name}."""
    db_var = crud.get_variable_by_name(db, env_name, var_name)
    if db_var is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variable no encontrada en el entorno.")
    return db_var

@app.put("/enviroments/{env_name}/variables/{var_name}", response_model=schemas.VariableOut, tags=["Variables"], summary="Actualizar COMPLETAMENTE una Variable")
def update_variable_full(env_name: str, var_name: str, var_update: schemas.VariableCreate, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: PUT /enviroments/{env_name}/variables/{var_name} (Actualización completa)."""
    db_var = crud.get_variable_by_name(db, env_name, var_name)
    if db_var is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variable no encontrada en el entorno.")
        
    # PUT: Actualización completa (partial=False)
    return crud.update_variable(db, db_var, var_update, partial=False)

@app.patch("/enviroments/{env_name}/variables/{var_name}", response_model=schemas.VariableOut, tags=["Variables"], summary="Actualizar PARCIALMENTE una Variable")
def update_variable_partial(env_name: str, var_name: str, var_update: schemas.VariableBase, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: PATCH /enviroments/{env_name}/variables/{var_name} (Actualización parcial)."""
    db_var = crud.get_variable_by_name(db, env_name, var_name)
    if db_var is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variable no encontrada en el entorno.")
        
    # PATCH: Actualización parcial (partial=True)
    return crud.update_variable(db, db_var, var_update, partial=True)

@app.delete("/enviroments/{env_name}/variables/{var_name}", status_code=status.HTTP_204_NO_CONTENT, tags=["Variables"], summary="Eliminar una Variable")
def delete_variable_resource(env_name: str, var_name: str, db: Session = Depends(get_db), user: str = Depends(authenticate_user)):
    """Requisito: DELETE /enviroments/{env_name}/variables/{var_name} (Código 204)."""
    db_var = crud.get_variable_by_name(db, env_name, var_name)
    if db_var is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variable no encontrada en el entorno.")
        
    crud.delete_variable(db, db_var)
    return # Retorna 204 No Content