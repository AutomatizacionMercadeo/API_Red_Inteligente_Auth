import logging
import time
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DisconnectionError, OperationalError
from contextlib import contextmanager
from typing import Generator
from app.core.config import settings

# Configurar logging específico para SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(
    logging.INFO if settings.DEBUG else logging.WARNING
)
logging.getLogger('sqlalchemy.pool').setLevel(
    logging.INFO if settings.DEBUG else logging.WARNING
)

logger = logging.getLogger(__name__)

def create_database_engine():
    """
    Crea el engine de SQLAlchemy optimizado para PostgreSQL
    """
    try:
        # Configuración del pool de conexiones
        pool_config = {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": settings.DB_POOL_PRE_PING,
            "pool_timeout": 30,
        }
        
        # Configuraciones adicionales del engine
        engine_config = {
            "echo": settings.DEBUG,
            "future": True,  # SQLAlchemy 2.0 style
            **pool_config
        }
        
        logger.info(f"Creando engine de base de datos para: {settings.DB_SERVER}/{settings.DB_NAME}")
        engine = create_engine(settings.database_url, **engine_config)
        
        return engine
        
    except Exception as e:
        logger.error(f"Error creando engine de base de datos: {e}")
        logger.error(f"URL de conexión (sin password): {settings.get_database_url_for_logging()}")
        raise

# Crear engine global
engine = create_database_engine()

# Crear sessionmaker con configuraciones optimizadas
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # Importante para evitar lazy loading issues
)

# Base para los modelos
Base = declarative_base()

# Metadata para las tablas
metadata = MetaData()

def get_db() -> Generator:
    """
    Dependency para obtener sesión de base de datos
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en sesión de base de datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_session():
    """
    Context manager para obtener sesión de base de datos
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Error en contexto de sesión: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_connection(max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """
    Prueba la conexión a la base de datos con reintentos
    
    Args:
        max_retries: Número máximo de reintentos
        retry_delay: Tiempo de espera entre reintentos en segundos
        
    Returns:
        bool: True si la conexión es exitosa
    """
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    logger.info(f"Conexión a PostgreSQL exitosa (intento {attempt + 1})")
                    return True
        except (OperationalError, DisconnectionError) as e:
            logger.warning(f"Error de conexión (intento {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Reintentando en {retry_delay} segundos...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Backoff exponencial
            else:
                logger.error("Se agotaron los reintentos de conexión")
        except Exception as e:
            logger.error(f"Error inesperado en conexión de BD: {e}")
            return False
    
    return False

def init_db():
    """
    Inicializa la base de datos verificando las tablas existentes
    """
    try:
        logger.info("Verificando esquema de base de datos...")
        
        # Verificar que las tablas principales existan
        with engine.connect() as connection:
            # Verificar tabla de usuarios
            result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'stg_personal'
            """))
            
            if result.scalar() == 0:
                raise Exception("Tabla stg_personal no encontrada")
            
            # Verificar tabla de verificaciones
            result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'user_pswr'
            """))
            
            if result.scalar() == 0:
                raise Exception("Tabla user_pswr no encontrada")
            
            logger.info("Esquema de base de datos verificado correctamente")
            
    except Exception as e:
        logger.error(f"Error verificando esquema de base de datos: {e}")
        raise

def close_db_connections():
    """
    Cierra todas las conexiones de base de datos de manera ordenada
    """
    try:
        engine.dispose()
        logger.info("Conexiones de base de datos cerradas correctamente")
    except Exception as e:
        logger.error(f"Error cerrando conexiones de base de datos: {e}")