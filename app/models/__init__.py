# app/models/__init__.py
from sqlalchemy.ext.declarative import declarative_base

# Base común para todos los modelos
Base = declarative_base()

# Importar todos los modelos
from .user import User
from .code_verification import CodeVerification

# Exportar para uso fácil
__all__ = ['Base', 'User', 'CodeVerification']