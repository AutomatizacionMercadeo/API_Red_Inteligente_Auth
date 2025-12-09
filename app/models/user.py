from sqlalchemy import Column, String, Date
from . import Base

class User(Base):
    """
    Modelo SQLAlchemy para la tabla stg_personal
    Contiene la información de los empleados/usuarios del sistema
    """
    __tablename__ = 'stg_personal'
    __table_args__ = {'schema': 'dbo'}
    
    # Campos principales
    cod_empleado = Column(String(50), primary_key=True, index=True)
    cod_tipo_doc = Column(String(10), nullable=True)
    nro_documento = Column(String(50), nullable=False, index=True)
    ds_empleado = Column(String(255), nullable=True)
    dt_nacimiento = Column(Date, nullable=True)
    correo = Column(String(255), nullable=True, index=True)
    movil = Column(String(50), nullable=True)
    cod_cargo = Column(String(50), nullable=True)
    ds_cargo = Column(String(255), nullable=True)
    ds_categoria = Column(String(100), nullable=True)
    cod_oficina_area = Column(String(50), nullable=True)
    dt_inicio_contrato = Column(Date, nullable=True)
    dt_fin_contrato = Column(Date, nullable=True)
    dt_actualizacion = Column(Date, nullable=True)
    
    def __repr__(self):
        return f"<User(cod_empleado='{self.cod_empleado}', nro_documento='{self.nro_documento}', ds_empleado='{self.ds_empleado}')>"
    
    def is_active(self) -> bool:
        """
        Verifica si el usuario tiene contrato activo
        """
        from datetime import date
        if self.dt_fin_contrato is None:
            return True
        return self.dt_fin_contrato >= date.today()