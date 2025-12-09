from pydantic import BaseModel, validator
from typing import Optional
import re


class ApiResponse(BaseModel):
    """Schema genérico para respuestas de la API"""
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Schema para respuestas de error"""
    success: bool = False
    message: str
    errors: Optional[list] = None
    error_code: Optional[str] = None


class RequestCodeRequest(BaseModel):
    """Schema para solicitar código"""
    document_number: str
    
    @validator('document_number')
    def validate_document_number(cls, v):
        clean_doc = re.sub(r'[^\d]', '', v)
        if len(clean_doc) < 3:
            raise ValueError('El número de documento debe tener al menos 3 dígitos')
        return clean_doc


class VerifyCodeRequest(BaseModel):
    """Schema para verificación de código"""
    document_number: str
    code: str
    
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