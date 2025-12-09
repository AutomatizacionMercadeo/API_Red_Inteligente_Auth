from fastapi import APIRouter, HTTPException, status, Request
from app.schemas.auth import (
    ApiResponse,
    VerifyCodeRequest,
    RequestCodeRequest
)
from app.services.code_service import CodeService
from app.core.email_verification import EmailService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/request-code",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Solicitar código de acceso",
    description="Genera y envía un código de 6 dígitos al correo del usuario"
)
async def request_code(request_data: RequestCodeRequest, request: Request):
    """
    Solicita un código de acceso para iniciar sesión.
    
    - **document_number**: Número de documento del usuario
    
    Retorna los datos necesarios para la siguiente vista (validación de código).
    """
    try:
        result = CodeService.generate_code(request_data.document_number)
        
        # Enviar código por correo electrónico
        email_sent = EmailService.send_verification_code(
            email=result["correo"],
            full_name=result["nombre"],
            code=result["code"]
        )
        
        if not email_sent:
            logger.warning(f"No se pudo enviar email a {result['correo']}, pero el código fue generado")
        
        response_data = {
            "document_number": request_data.document_number,
            "nombre": result["nombre"],
            "email_hint": result["correo"][:3] + "***@" + result["correo"].split("@")[1] if result["correo"] else None,
            "expires_in_minutes": settings.CODE_EXPIRATION_MINUTES,
        }
        
        # Solo incluir código en modo debug
        if settings.DEBUG:
            response_data["code_debug"] = result["code"]
        
        return ApiResponse(
            success=True,
            message="Código de verificación enviado al correo electrónico registrado.",
            data=response_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en request_code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al solicitar código: {str(e)}"
        )


@router.post(
    "/verify-code",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar código de acceso",
    description="Valida el código de 6 dígitos ingresado por el usuario"
)
async def verify_code(verify_data: VerifyCodeRequest, request: Request):
    """
    Verifica el código de acceso.
    
    - **document_number**: Número de documento del usuario
    - **code**: Código de 6 dígitos recibido por correo
    
    Retorna éxito si el código es válido, o un mensaje de error apropiado.
    """
    result = CodeService.validate_code(verify_data.document_number, verify_data.code)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    
    return ApiResponse(
        success=True,
        message="Código verificado correctamente. Acceso permitido.",
        data=result["data"]
    )


@router.post(
    "/resend-code",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="Reenviar código de acceso",
    description="Genera y envía un nuevo código de 6 dígitos al correo del usuario"
)
async def resend_code(request_data: RequestCodeRequest, request: Request):
    """
    Reenvía un nuevo código de acceso.
    
    - **document_number**: Número de documento del usuario
    
    Limitaciones:
    - Debe esperar 2 minutos entre reenvíos
    - Máximo 5 reenvíos por hora
    """
    try:
        result = CodeService.resend_code(request_data.document_number)
        
        # Enviar código por correo electrónico
        email_sent = EmailService.send_verification_code(
            email=result["correo"],
            full_name=result["nombre"],
            code=result["code"]
        )
        
        if not email_sent:
            logger.warning(f"No se pudo enviar email a {result['correo']}, pero el código fue generado")
        
        response_data = {
            "document_number": request_data.document_number,
            "expires_in_minutes": settings.CODE_EXPIRATION_MINUTES,
        }
        
        # Solo incluir código en modo debug
        if settings.DEBUG:
            response_data["code_debug"] = result["code"]
        
        return ApiResponse(
            success=True,
            message="Nuevo código de verificación enviado al correo electrónico registrado.",
            data=response_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en resend_code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al reenviar código: {str(e)}"
        )