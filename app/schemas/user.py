from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
import re


class UserLogin(BaseModel):
    """
    Schema para login de usuario
    """
    document_number: str
    code: str   # Código de 6 dígitos enviado por email
    
    @validator('document_number')
    def validate_document_number(cls, v):
        clean_doc = re.sub(r'[^\d]', '', v)
        if len(clean_doc) < 3:
            raise ValueError('El número de documento debe tener al menos 3 dígitos')
        return clean_doc
    
    @validator('code')
    def validate_code(cls, v):
        if not re.match(r'^\d{6}$', v):
            raise ValueError('El código debe ser un número de 6 dígitos')
        return v


class UserResponse(BaseModel):
    """
    Schema para respuesta de usuario
    """
    nro_documento: int
    email: EmailStr
    full_name: str
    phone: str
    
    class Config:
        from_attributes = True


class CodeGeneration(BaseModel):
    """
    Schema para generación de código
    """
    email: EmailStr
    document_number: str
    
    @validator('document_number')
    def validate_document_number(cls, v):
        clean_doc = re.sub(r'[^\d]', '', v)
        if len(clean_doc) < 3:
            raise ValueError('El número de documento debe tener al menos 3 dígitos')
        return clean_doc