# app/middleware.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging de requests y responses.
    Registra: método, path, status code y tiempo de respuesta.
    """
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        # Log del request entrante
        logger.info(f"→ {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log del response
            logger.info(
                f"← {request.method} {request.url.path} "
                f"[{response.status_code}] {process_time:.3f}s"
            )
            
            # Agregar header con tiempo de procesamiento
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"✗ {request.method} {request.url.path} "
                f"ERROR: {str(e)} ({process_time:.3f}s)"
            )
            raise


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware para manejo global de errores no capturados.
    Convierte excepciones en respuestas JSON consistentes.
    """
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            return await call_next(request)
        except ValueError as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Valor inválido: {str(e)}"}
            )
        except Exception as e:
            logger.exception("Error interno no manejado")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Error interno del servidor",
                    "error": str(e) if logger.level == logging.DEBUG else "Internal error"
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware simple de rate limiting (limitación de peticiones).
    Útil para proteger la API de abuso.
    """
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, ...)]}
    
    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.client.host
        current_time = time.time()
        
        # Limpiar requests antiguos
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.window_seconds
            ]
        else:
            self.requests[client_ip] = []
        
        # Verificar límite
        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit excedido. Máximo {self.max_requests} requests por {self.window_seconds}s"
                }
            )
        
        # Registrar request
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.max_requests - len(self.requests[client_ip])
        )
        return response