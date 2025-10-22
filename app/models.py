# app/models.py
from sqlalchemy import Column, String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

# Clase base para todos los modelos
Base = declarative_base()

class Environment(Base):
    __tablename__ = 'environments'
    
    # name es la clave primaria y el URL slug
    name = Column(String, primary_key=True, index=True) 
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relación: Un entorno puede tener muchas variables
    variables = relationship("Variable", back_populates="environment", cascade="all, delete-orphan")

class Variable(Base):
    __tablename__ = 'variables'

    # name y env_name juntos forman la clave primaria compuesta
    name = Column(String, primary_key=True, index=True)
    env_name = Column(String, ForeignKey('environments.name'), primary_key=True) 
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relación: Una variable pertenece a un entorno
    environment = relationship("Environment", back_populates="variables")