from sqlalchemy import Column, String, Integer, BigInteger, DateTime, func
from typing import Optional
from datetime import datetime, timedelta
from app.core.config import settings
from . import Base

class CodeVerification(Base):
    __tablename__ = 'user_pswr'
    __table_args__ = {'schema': 'dbo'}
    
    id = Column(BigInteger, primary_key=True, index=True)
    correo = Column(String(255), nullable=False, index=True)
    movil = Column(BigInteger, nullable=False, index=True)
    pswr = Column(String(255), nullable=False, index=True)
    time_stamp_generacion = Column(DateTime, nullable=False, default=func.now())
    time_stamp_vencimiento = Column(DateTime, nullable=False)
    revoked = Column(Integer, nullable=False, default=0, index=True)
    resend_count = Column(Integer, nullable=False, default=0)
    last_resend_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<CodeVerification(id={self.id}, correo='{self.correo}', revoked={self.revoked})>"
    
    def is_valid(self) -> bool:
        if self.revoked != 0:
            return False
        return datetime.utcnow() <= self.time_stamp_vencimiento
    
    def mark_as_revoked(self) -> None:
        self.revoked = 1
    
    def can_resend(self) -> tuple:
        """
        Verifica si se puede reenviar el código.
        Retorna (puede_reenviar, mensaje_error)
        """
        now = datetime.utcnow()
        
        # Verificar delay mínimo
        if self.last_resend_at:
            time_since_last = (now - self.last_resend_at).total_seconds() / 60
            if time_since_last < settings.CODE_RESEND_DELAY_MINUTES:
                wait_time = int(settings.CODE_RESEND_DELAY_MINUTES - time_since_last) + 1
                return False, f"Debe esperar {wait_time} minuto(s) antes de solicitar un nuevo código."
        
        # Verificar límite por hora
        if self.resend_count >= settings.CODE_MAX_RESEND_PER_HOUR:
            if self.time_stamp_generacion:
                hours_since_first = (now - self.time_stamp_generacion).total_seconds() / 3600
                if hours_since_first < 1:
                    return False, "Ha excedido el límite de reenvíos por hora. Intente más tarde."
                else:
                    # Reiniciar contador si pasó más de 1 hora
                    self.reset_resend_count()
        
        return True, ""
    
    def increment_resend(self) -> None:
        self.resend_count += 1
        self.last_resend_at = datetime.utcnow()
    
    def reset_resend_count(self) -> None:
        self.resend_count = 0
        self.last_resend_at = None
    
    def time_until_expiry(self) -> Optional[int]:
        if datetime.utcnow() > self.time_stamp_vencimiento:
            return None
        time_diff = self.time_stamp_vencimiento - datetime.utcnow()
        return int(time_diff.total_seconds() / 60)
    
    @classmethod
    def create_code(cls, document_number: int, correo: str, movil: int, pswr: str, expiration_minutes: int = None) -> 'CodeVerification':
        if expiration_minutes is None:
            expiration_minutes = settings.CODE_EXPIRATION_MINUTES
            
        expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        return cls(
            id=document_number,
            correo=correo,
            movil=movil,
            pswr=pswr,
            time_stamp_generacion=datetime.utcnow(),
            time_stamp_vencimiento=expires_at,
            revoked=0,
            resend_count=0,
            last_resend_at=None
        )