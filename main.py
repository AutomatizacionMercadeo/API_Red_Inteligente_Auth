import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn, os
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db, test_connection
from app.api.v1.auth import router as auth_router

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manejador del ciclo de vida de la aplicación
    """
    # Startup
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    
    # Probar conexión a base de datos
    try:
        logger.info("Probando conexión a PostgreSQL...")
        if test_connection():
            logger.info("Conexión a PostgreSQL exitosa")
            logger.info("Sistema de autenticación usando base de datos PostgreSQL")
        else:
            logger.error("Error de conexión a PostgreSQL")
            raise Exception("No se pudo conectar a la base de datos")
    except Exception as e:
        logger.error(f"Error crítico de base de datos: {e}")
        logger.error("La aplicación no puede iniciar sin base de datos")
        raise
    
    # Inicializar base de datos (verificar esquema)
    try:
        logger.info("Verificando esquema de base de datos...")
        init_db()
        logger.info("Esquema de base de datos verificado correctamente")
    except Exception as e:
        logger.error(f"Error verificando esquema de BD: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación...")

# Crear instancia de FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API Backend para el inicio de sesión y autenticación de usuarios de Red Inteligente",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Endpoint básico de salud
@app.get("/", tags=["Health Check"])
async def root():
    """
    Endpoint de salud de la API
    """
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "healthy",
        "database": "PostgreSQL"
    }

@app.get("/api/red-inteligente/v1/health", tags=["Health Check"])
async def health_check():
    """Endpoint para verificar el estado de la aplicación"""
    try:
        db_status = "connected" if test_connection() else "disconnected"
        
        return {
            "status": "healthy",
            "database": {"status": db_status, "type": "PostgreSQL"},
        }
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": {"status": "error"},
        }

# Incluir routers de la API
app.include_router(auth_router, prefix="/api/red-inteligente/v1")

# Manejador global de excepciones
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": exc.status_code
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Error interno del servidor: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Error interno del servidor",
            "error_code": 500
        }
    )

if __name__ == "__main__":
    # Azure inyecta el puerto via variable de entorno
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )