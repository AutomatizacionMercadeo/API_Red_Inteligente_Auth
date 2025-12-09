from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy import text
from app.models.code_verification import CodeVerification
from app.core.database import SessionLocal
from app.core.config import settings
from passlib.hash import argon2
import secrets
import logging

logger = logging.getLogger(__name__)

class CodeService:
    """
    Servicio para manejar la generación, validación y reenvío de códigos de validación.
    """
    
    @staticmethod
    def hash_code(code: str) -> str:
        return argon2.hash(code)
    
    @staticmethod
    def verify_code_hash(code: str, hashed_code: str) -> bool:
        try:
            return argon2.verify(code, hashed_code)
        except Exception:
            return False

    @staticmethod
    def generate_code(document_number: str, is_resend: bool = False) -> dict:
        """
        Genera un código de 6 dígitos si el usuario existe y está activo.
        """
        db = SessionLocal()
        try:
            # Validar existencia del usuario en dbo.stg_personal
            result = db.execute(
                text("""
                    SELECT nro_documento, correo, movil, dt_fin_contrato, ds_empleado
                    FROM dbo.stg_personal
                    WHERE nro_documento = :document_number
                """),
                {"document_number": document_number}
            )
            user = result.fetchone()

            if not user:
                logger.warning(f"Usuario con documento {document_number} no encontrado.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Usuario no encontrado en la base de datos."
                )

            # Validar que el contrato no haya finalizado
            dt_fin_contrato = user.dt_fin_contrato
            if dt_fin_contrato and dt_fin_contrato < datetime.utcnow().date():
                logger.warning(f"Usuario con documento {document_number} tiene contrato finalizado.")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="El usuario no está activo debido a la finalización del contrato."
                )

            # Generar un código único de 6 dígitos
            code = ''.join(secrets.choice("0123456789") for _ in range(6))
            
            # Crear hash Argon2 del código
            hashed_code = CodeService.hash_code(code)

            # Convertir movil a entero
            movil_int = int(user.movil) if user.movil else 0

            # Buscar si ya existe un registro
            existing_code = db.query(CodeVerification).filter(
                CodeVerification.id == int(document_number)
            ).first()

            if existing_code:
                # Actualizar registro existente
                existing_code.correo = user.correo
                existing_code.movil = movil_int
                existing_code.pswr = hashed_code
                existing_code.time_stamp_generacion = datetime.utcnow()
                existing_code.time_stamp_vencimiento = datetime.utcnow() + timedelta(minutes=settings.CODE_EXPIRATION_MINUTES)
                existing_code.revoked = 0
                
                if is_resend:
                    existing_code.resend_count = (existing_code.resend_count or 0) + 1
                    existing_code.last_resend_at = datetime.utcnow()
                    #logger.info(f"Reenvío #{existing_code.resend_count} para {document_number}")
                else:
                    existing_code.resend_count = 0
                    existing_code.last_resend_at = None
            else:
                # Crear nuevo registro
                code_instance = CodeVerification.create_code(
                    document_number=int(document_number),
                    correo=user.correo,
                    movil=movil_int,
                    pswr=hashed_code
                )
                db.add(code_instance)

            db.commit()

            logger.info(f"Código generado para {user.correo}")
            
            return {
                "correo": user.correo,
                "nombre": user.ds_empleado,
                "code": code
            }
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error al generar código para {document_number}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al generar el código de validación: {str(e)}"
            )
        finally:
            db.close()

    @staticmethod
    def validate_code(document_number: str, code: str) -> dict:
        """
        Valida si el código ingresado es correcto.
        """
        db = SessionLocal()
        try:
            code_instance = db.query(CodeVerification).filter(
                CodeVerification.id == int(document_number)
            ).first()
            
            if not code_instance:
                logger.warning(f"No se encontró código para {document_number}.")
                return {
                    "success": False,
                    "message": "No se encontró un código de verificación para este usuario.",
                    "data": None
                }
            
            if code_instance.revoked != 0:
                logger.warning(f"Código ya fue usado para {document_number}.")
                return {
                    "success": False,
                    "message": "El código ya fue utilizado. Solicite uno nuevo.",
                    "data": None
                }
            
            if code_instance.time_stamp_vencimiento < datetime.utcnow():
                logger.warning(f"Código expirado para {document_number}.")
                return {
                    "success": False,
                    "message": "El código ha expirado. Solicite uno nuevo.",
                    "data": None
                }
            
            if not CodeService.verify_code_hash(code, code_instance.pswr):
                logger.warning(f"Código incorrecto para {document_number}.")
                return {
                    "success": False,
                    "message": "El código ingresado es incorrecto.",
                    "data": None
                }
            
            code_instance.mark_as_revoked()
            db.commit()
            
            user_result = db.execute(
                text("""
                    SELECT nro_documento, ds_empleado, correo, ds_cargo, cod_oficina_area
                    FROM dbo.stg_personal
                    WHERE nro_documento = :document_number
                """),
                {"document_number": document_number}
            )
            user = user_result.fetchone()
            
            logger.info(f"Código validado correctamente para {document_number}.")
            
            return {
                "success": True,
                "message": "Código verificado correctamente.",
                "data": {
                    "document_number": document_number,
                    "nombre": user.ds_empleado if user else None,
                    "correo": user.correo if user else None,
                    "cargo": user.ds_cargo if user else None,
                    "oficina": user.cod_oficina_area if user else None
                }
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al validar código para {document_number}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al validar el código de validación."
            )
        finally:
            db.close()

    @staticmethod
    def resend_code(document_number: str) -> dict:
        """
        Reenvía un nuevo código al usuario con validaciones de límite.
        """
        db = SessionLocal()
        try:
            # Verificar si existe un código previo
            existing_code = db.query(CodeVerification).filter(
                CodeVerification.id == int(document_number)
            ).first()
            
            if existing_code:
                # Log para depuración
                #logger.info(f"Estado actual - resend_count: {existing_code.resend_count}, last_resend_at: {existing_code.last_resend_at}")
                
                # Validar si puede reenviar
                can_resend, error_message = existing_code.can_resend()
                #logger.info(f"can_resend: {can_resend}, error: {error_message}")
                
                if not can_resend:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=error_message
                    )
            
            # Cerrar esta sesión
            db.close()
            
            # Generar nuevo código indicando que es reenvío
            result = CodeService.generate_code(document_number, is_resend=True)
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al reenviar código para {document_number}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al reenviar el código: {str(e)}"
            )
        finally:
            try:
                db.close()
            except:
                pass

    @staticmethod
    def cleanup_expired_codes() -> int:
        """
        Limpia los códigos expirados de la base de datos.
        """
        db = SessionLocal()
        try:
            deleted_count = db.query(CodeVerification).filter(
                CodeVerification.time_stamp_vencimiento < datetime.utcnow(),
                CodeVerification.revoked == 0
            ).delete()
            
            db.commit()
            logger.info(f"Se eliminaron {deleted_count} códigos expirados.")
            return deleted_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al limpiar códigos expirados: {e}")
            return 0
        finally:
            db.close()