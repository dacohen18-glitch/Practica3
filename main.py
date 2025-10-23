from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
from starlette.requests import Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.utils import get_openapi
import os
import urllib.parse
import logging

from app import schemas, crud
from app.database import get_db, create_db_tables
from app.middleware import LoggingMiddleware, ErrorHandlerMiddleware  # NUEVO
from app.exceptions import (  # NUEVO
    EnvironmentNotFoundException,
    EnvironmentAlreadyExistsException,
    VariableNotFoundException,
    VariableAlreadyExistsException,
    InvalidCredentialsException
)

# ===== CONFIGURACIÓN DE LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== INICIALIZACIÓN DE BASE DE DATOS =====
try:
    create_db_tables()
    logger.info("✓ Tablas de base de datos creadas exitosamente")
except Exception as e:
    logger.error(f"⚠️ ERROR AL CREAR TABLAS O CONECTAR DB: {e}")
    raise

# ===== CONFIGURACIÓN DE AUTENTICACIÓN =====
API_USERNAME = os.environ.get("API_USER", "admin")
API_PASSWORD = os.environ.get("API_PASSWORD", "supersecrettoken")

security = HTTPBasic()

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Verifica credenciales básicas (admin por defecto)."""
    if credentials.username != API_USERNAME or credentials.password != API_PASSWORD:
        logger.warning(f"Intento de autenticación fallido: {credentials.username}")
        raise InvalidCredentialsException()
    logger.debug(f"Usuario autenticado: {credentials.username}")
    return credentials.username

# ===== CREACIÓN DE LA APLICACIÓN =====
app = FastAPI(
    title="Config Service API",
    description="Servicio RESTful de Gestión de Configuración Dinámica (Config Service).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Equipo de Desarrollo",
        "email": "dev@configservice.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# ===== AGREGAR MIDDLEWARES =====
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)

# ===== PERSONALIZAR ESQUEMA OPENAPI =====
def custom_openapi():
    """Personaliza el esquema OpenAPI con información de seguridad."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Agregar esquema de autenticación HTTP Basic
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBasic": {
            "type": "http",
            "scheme": "basic",
            "description": "Autenticación HTTP Basic. Usuario y contraseña configurados via variables de entorno."
        }
    }
    
    # Aplicar seguridad global
    openapi_schema["security"] = [{"HTTPBasic": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ===== FUNCIONES AUXILIARES =====
def _get_pagination_urls(
    request: Request, 
    count: int, 
    page: int, 
    size: int, 
    endpoint_name: str, 
    env_name: Optional[str] = None
):
    """Construye las URLs next/previous para respuestas paginadas."""
    path = request.url_for(endpoint_name, env_name=env_name) if env_name else request.url_for(endpoint_name)
    next_url = previous_url = None

    if (page * size) < count:
        next_url = urllib.parse.urljoin(str(request.base_url), f"{path}?page={page + 1}&size={size}")
    if page > 1:
        previous_url = urllib.parse.urljoin(str(request.base_url), f"{path}?page={page - 1}&size={size}")

    return next_url, previous_url

# ===== ENDPOINTS =====

@app.get("/", include_in_schema=False)
def root():
    """Redirige al endpoint de documentación."""
    return RedirectResponse(url="/docs")

@app.get(
    "/status/", 
    tags=["Salud"], 
    summary="Verificar estado del servicio",
    response_description="Estado del servicio",
    responses={
        200: {
            "description": "Servicio funcionando correctamente",
            "content": {
                "application/json": {
                    "example": {"status": "pong"}
                }
            }
        }
    }
)
def health_check():
    """
    Health Check del servicio.
    
    Retorna un simple 'pong' para verificar que el servicio está activo.
    Este endpoint no requiere autenticación.
    """
    return {"status": "pong"}

# ===== ENDPOINTS DE ENTORNOS =====

@app.get(
    "/enviroments/", 
    response_model=schemas.PaginatedResponse, 
    tags=["Entornos"], 
    summary="Listar entornos (paginado)",
    response_description="Lista paginada de entornos"
)
def list_environments(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(10, ge=1, le=100, description="Tamaño de página"),
    user: str = Depends(authenticate_user)
):
    """
    Obtiene una lista paginada de todos los entornos.
    
    - **page**: Número de página (mínimo 1)
    - **size**: Cantidad de elementos por página (1-100)
    
    Retorna un objeto con: count, next, previous, results
    """
    skip = (page - 1) * size
    environments, count = crud.get_environments(db, skip=skip, limit=size)
    next_url, prev_url = _get_pagination_urls(request, count, page, size, 'list_environments')

    logger.info(f"Listado de entornos - Página {page}, Total: {count}")
    
    return {
        "count": count,
        "next": next_url,
        "previous": prev_url,
        "results": [schemas.EnvironmentOut.model_validate(e) for e in environments]
    }

@app.post(
    "/enviroments/", 
    response_model=schemas.EnvironmentOut, 
    status_code=201, 
    tags=["Entornos"],
    summary="Crear un nuevo entorno",
    responses={
        201: {"description": "Entorno creado exitosamente"},
        400: {"description": "El entorno ya existe"},
        401: {"description": "No autenticado"}
    }
)
def create_environment(
    env_in: schemas.EnvironmentCreate, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Crea un nuevo entorno.
    
    - **name**: Nombre único del entorno (debe ser un URL slug válido)
    - **description**: Descripción opcional del entorno
    """
    if crud.get_environment_by_name(db, env_in.name):
        raise EnvironmentAlreadyExistsException(env_in.name)
    
    env = crud.create_environment(db, env_in)
    logger.info(f"Entorno creado: {env.name} por usuario {user}")
    return env

@app.get(
    "/enviroments/{env_name}/", 
    response_model=schemas.EnvironmentOut, 
    tags=["Entornos"],
    summary="Obtener detalles de un entorno",
    responses={
        200: {"description": "Entorno encontrado"},
        404: {"description": "Entorno no encontrado"}
    }
)
def get_environment(
    env_name: str, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Obtiene los detalles de un entorno específico por su nombre.
    """
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise EnvironmentNotFoundException(env_name)
    return env

@app.put(
    "/enviroments/{env_name}/", 
    response_model=schemas.EnvironmentOut, 
    tags=["Entornos"],
    summary="Actualizar un entorno (completo)"
)
def update_environment_put(
    env_name: str, 
    env_update: schemas.EnvironmentUpdate, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Actualiza un entorno existente (PUT - actualización completa).
    """
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise EnvironmentNotFoundException(env_name)
    
    updated = crud.update_environment(db, env, env_update)
    logger.info(f"Entorno actualizado (PUT): {env_name} por {user}")
    return updated

@app.patch(
    "/enviroments/{env_name}/", 
    response_model=schemas.EnvironmentOut, 
    tags=["Entornos"],
    summary="Actualizar un entorno (parcial)"
)
def update_environment_patch(
    env_name: str, 
    env_update: schemas.EnvironmentUpdate, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Actualiza parcialmente un entorno existente (PATCH - actualización parcial).
    Solo los campos proporcionados serán actualizados.
    """
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise EnvironmentNotFoundException(env_name)
    
    updated = crud.update_environment(db, env, env_update)
    logger.info(f"Entorno actualizado (PATCH): {env_name} por {user}")
    return updated

@app.delete(
    "/enviroments/{env_name}/", 
    status_code=204, 
    tags=["Entornos"],
    summary="Eliminar un entorno",
    responses={
        204: {"description": "Entorno eliminado exitosamente"},
        404: {"description": "Entorno no encontrado"}
    }
)
def delete_environment(
    env_name: str, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Elimina un entorno y todas sus variables asociadas.
    
    ⚠️ ATENCIÓN: Esta acción es irreversible.
    """
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise EnvironmentNotFoundException(env_name)
    
    crud.delete_environment(db, env)
    logger.warning(f"Entorno eliminado: {env_name} por {user}")
    return

# ===== ENDPOINTS DE VARIABLES =====

@app.get(
    "/enviroments/{env_name}/variables", 
    response_model=schemas.PaginatedResponse, 
    tags=["Variables"],
    summary="Listar variables de un entorno (paginado)"
)
def list_variables(
    request: Request,
    env_name: str,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(10, ge=1, le=100, description="Tamaño de página"),
    user: str = Depends(authenticate_user)
):
    """
    Obtiene una lista paginada de todas las variables de un entorno.
    """
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise EnvironmentNotFoundException(env_name)

    skip = (page - 1) * size
    variables, count = crud.get_variables_by_env(db, env_name, skip=skip, limit=size)
    next_url, prev_url = _get_pagination_urls(request, count, page, size, 'list_variables', env_name=env_name)

    logger.info(f"Listado de variables de '{env_name}' - Página {page}, Total: {count}")

    return {
        "count": count,
        "next": next_url,
        "previous": prev_url,
        "results": [schemas.VariableOut.model_validate(v) for v in variables]
    }

@app.post(
    "/enviroments/{env_name}/variables", 
    response_model=schemas.VariableOut, 
    status_code=201, 
    tags=["Variables"],
    summary="Crear una nueva variable"
)
def create_variable(
    env_name: str, 
    var_in: schemas.VariableCreate, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Crea una nueva variable en un entorno específico.
    
    - **name**: Nombre único de la variable (formato UPPER_SNAKE_CASE recomendado)
    - **value**: Valor de la variable
    - **description**: Descripción opcional
    - **is_sensitive**: Si es sensible (contraseña, token, etc.)
    """
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise EnvironmentNotFoundException(env_name)

    if crud.get_variable_by_name(db, env_name, var_in.name):
        raise VariableAlreadyExistsException(var_in.name, env_name)
    
    var = crud.create_variable(db, env_name, var_in)
    logger.info(f"Variable creada: {var.name} en {env_name} por {user}")
    return var

@app.get(
    "/enviroments/{env_name}/variables/{var_name}", 
    response_model=schemas.VariableOut, 
    tags=["Variables"],
    summary="Obtener detalles de una variable"
)
def get_variable(
    env_name: str, 
    var_name: str, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Obtiene los detalles de una variable específica.
    """
    var = crud.get_variable_by_name(db, env_name, var_name)
    if not var:
        raise VariableNotFoundException(var_name, env_name)
    return var

@app.put(
    "/enviroments/{env_name}/variables/{var_name}", 
    response_model=schemas.VariableOut, 
    tags=["Variables"],
    summary="Actualizar una variable (completo)"
)
def update_variable_put(
    env_name: str, 
    var_name: str, 
    var_update: schemas.VariableBase, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Actualiza una variable existente (PUT - actualización completa).
    """
    var = crud.get_variable_by_name(db, env_name, var_name)
    if not var:
        raise VariableNotFoundException(var_name, env_name)
    
    updated = crud.update_variable(db, var, var_update, partial=False)
    logger.info(f"Variable actualizada (PUT): {var_name} en {env_name} por {user}")
    return updated

@app.patch(
    "/enviroments/{env_name}/variables/{var_name}", 
    response_model=schemas.VariableOut, 
    tags=["Variables"],
    summary="Actualizar una variable (parcial)"
)
def update_variable_patch(
    env_name: str, 
    var_name: str, 
    var_update: schemas.VariableBase, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Actualiza parcialmente una variable (PATCH - actualización parcial).
    Solo los campos proporcionados serán actualizados.
    """
    var = crud.get_variable_by_name(db, env_name, var_name)
    if not var:
        raise VariableNotFoundException(var_name, env_name)
    
    updated = crud.update_variable(db, var, var_update, partial=True)
    logger.info(f"Variable actualizada (PATCH): {var_name} en {env_name} por {user}")
    return updated

@app.delete(
    "/enviroments/{env_name}/variables/{var_name}", 
    status_code=204, 
    tags=["Variables"],
    summary="Eliminar una variable"
)
def delete_variable(
    env_name: str, 
    var_name: str, 
    db: Session = Depends(get_db), 
    user: str = Depends(authenticate_user)
):
    """
    Elimina una variable de un entorno.
    """
    var = crud.get_variable_by_name(db, env_name, var_name)
    if not var:
        raise VariableNotFoundException(var_name, env_name)
    
    crud.delete_variable(db, var)
    logger.warning(f"Variable eliminada: {var_name} de {env_name} por {user}")
    return

# ===== ENDPOINT DE CONSUMO MASIVO =====

@app.get(
    "/enviroments/{env_name}.json", 
    tags=["Consumo Masivo"], 
    summary="Obtener JSON plano de configuración",
    response_description="Configuración completa en formato JSON plano",
    responses={
        200: {
            "description": "JSON plano con todas las variables del entorno",
            "content": {
                "application/json": {
                    "example": {
                        "DB_URL": "postgres://prod_user:prod_pass@prod-db.com/main",
                        "FEATURE_NEW_UI": "False",
                        "API_TIMEOUT_MS": "5000",
                        "LOG_LEVEL": "WARNING"
                    }
                }
            }
        },
        404: {"description": "Entorno no encontrado"}
    }
)
def get_environment_config(env_name: str, db: Session = Depends(get_db)):
    """
    **Endpoint más importante:** Devuelve toda la configuración de un entorno en formato JSON plano.
    
    Este endpoint está diseñado para ser consumido por aplicaciones cliente que necesitan
    cargar todas las variables de configuración de un entorno específico.
    
    ⚠️ NOTA: Este endpoint NO requiere autenticación para facilitar el consumo por aplicaciones.
    """
    env = crud.get_environment_by_name(db, env_name)
    if not env:
        raise EnvironmentNotFoundException(env_name)
    
    config = crud.get_config_json_for_env(db, env_name)
    logger.info(f"Configuración masiva consultada para: {env_name}")
    return JSONResponse(content=config)

# ===== ENDPOINT DE ESQUEMA OPENAPI =====

@app.get("/schema", include_in_schema=False, tags=["Documentación"])
def get_openapi_schema():
    """
    Descarga el esquema OpenAPI completo en formato JSON.
    
    Útil para generar clientes, documentación externa, o herramientas de testing.
    """
    return JSONResponse(content=app.openapi())