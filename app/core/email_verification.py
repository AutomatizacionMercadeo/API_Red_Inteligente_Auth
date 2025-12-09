# app/core/email_verification.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio de email usando SMTP (Office 365)
    Para envío de códigos de verificación de acceso
    """
    
    @staticmethod
    def _create_smtp_connection():
        """
        Crear conexión SMTP con el servidor configurado
        
        Returns:
            smtplib.SMTP: Conexión SMTP configurada
        """
        try:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            logger.debug(f"Conexión SMTP establecida con {settings.SMTP_HOST}")
            return server
            
        except Exception as e:
            logger.error(f"Error al conectar con servidor SMTP: {e}")
            raise
    
    @staticmethod
    def _send_email(to_email: str, subject: str, html_body: str, text_body: str = None):
        """
        Enviar email usando SMTP configurado
        
        Args:
            to_email: Email destino
            subject: Asunto del email
            html_body: Contenido HTML del email
            text_body: Contenido texto plano (opcional)
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            with EmailService._create_smtp_connection() as server:
                server.send_message(msg)
            
            logger.info(f"Email enviado a {to_email}")
            
        except Exception as e:
            logger.error(f"Error al enviar email a {to_email}: {e}")
            raise

    @staticmethod
    def send_verification_code(email: str, full_name: str, code: str) -> bool:
        """
        Enviar email con código de verificación de 6 dígitos
        
        Args:
            email: Email del usuario
            full_name: Nombre completo del usuario  
            code: Código de 6 dígitos
            
        Returns:
            bool: True si se envió correctamente, False si hubo error
        """
        try:
            subject = "🔐 Tu código de acceso - Red Inteligente"

            html_body = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Código de Acceso - Red Inteligente</title>
            </head>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f4f4f4;">
                <div style="background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    
                    <!-- Header -->
                    <div style="background: #04AF5D; color: white; padding: 30px; text-align: center;">
                        <h1 style="margin: 0; font-size: 28px;">🔐 Red Inteligente</h1>
                        <p style="margin: 10px 0 0 0; font-size: 16px;">Código de Acceso</p>
                    </div>
                    
                    <!-- Content -->
                    <div style="padding: 30px;">
                        <h2 style="color: #333; margin-top: 0;">Hola {full_name},</h2>
                        
                        <p style="color: #555;">Has solicitado acceso a <strong>Red Inteligente</strong>. Usa el siguiente código para iniciar sesión:</p>
                        
                        <!-- Code Box -->
                        <div style="background: #04AF5D; color: white; font-size: 32px; font-weight: bold; letter-spacing: 8px; padding: 25px 20px; border-radius: 10px; text-align: center; margin: 30px 0; font-family: 'Courier New', monospace;">
                            {code}
                        </div>
                        
                        <!-- Warning -->
                        <div style="background: #fff3cd; border: 1px solid #ffc107; border-left: 4px solid #ffc107; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <strong style="color: #856404;">⏱️ Este código expira en {settings.CODE_EXPIRATION_MINUTES} minutos.</strong>
                        </div>
                        
                        <!-- Info -->
                        <div style="background: #e7f3ff; border: 1px solid #b6d4fe; border-left: 4px solid #0d6efd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <strong style="color: #084298;">🛡️ Seguridad:</strong>
                            <span style="color: #084298;"> Si no solicitaste este código, ignora este mensaje. Nunca compartas tu código con nadie.</span>
                        </div>
                        
                        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 30px 0;">
                        
                        <p style="font-size: 13px; color: #6c757d; text-align: center;">
                            📧 Este es un email automático, por favor no respondas a esta dirección.
                        </p>
                    </div>
                    
                    <!-- Footer -->
                    <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #6c757d; border-top: 1px solid #dee2e6;">
                        <p style="margin: 0;">&copy; 2025 Red Inteligente - Grupo Reditos</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            RED INTELIGENTE - Código de Acceso
            
            Hola {full_name},
            
            Tu código de acceso es: {code}
            
            Este código expira en {settings.CODE_EXPIRATION_MINUTES} minutos.
            
            Si no solicitaste este código, ignora este mensaje.
            
            Saludos,
            Red Inteligente - Grupo Reditos
            """
            
            EmailService._send_email(email, subject, html_body, text_body)
            
            logger.info(f"Código de verificación enviado a {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar código a {email}: {e}")
            if settings.DEBUG:
                print(f"""
                ========================================
                ERROR AL ENVIAR EMAIL - FALLBACK CONSOLA
                ========================================
                Para: {email}
                Nombre: {full_name}
                CÓDIGO: {code}
                ERROR: {str(e)}
                ========================================
                """)
            return False