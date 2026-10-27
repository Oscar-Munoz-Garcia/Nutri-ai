from sqlalchemy import Column, String, Float, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    perfil = relationship("PerfilDB", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    pantry = relationship("PantryDB", back_populates="usuario", cascade="all, delete-orphan")
    recetas = relationship("RecetaDB", back_populates="usuario", cascade="all, delete-orphan")
    registros = relationship("RegistroConsumoDB", back_populates="usuario", cascade="all, delete-orphan")


class PerfilDB(Base):
    __tablename__ = "perfil"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, unique=True)
    usuario = relationship("UsuarioDB", back_populates="perfil")

    nombre = Column(String, default="Usuario")
    edad = Column(Integer, default=24)
    peso_kg = Column(Float, default=75.0)
    altura_cm = Column(Float, default=178.0)
    genero = Column(String, default="hombre")
    nivel_actividad = Column(String, default="moderado")
    modo_objetivo = Column(String, default="manual_macros")
    
    calorias_objetivo = Column(Float, default=2200.0)
    proteinas_objetivo = Column(Float, default=160.0)
    carbohidratos_objetivo = Column(Float, default=210.0)
    grasas_objetivo = Column(Float, default=70.0)

class PesoHistorialDB(Base):
    __tablename__ = "peso_historial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha = Column(String, index=True)
    peso_kg = Column(Float)


class PantryDB(Base):
    __tablename__ = "pantry"

    id = Column(String, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario = relationship("UsuarioDB", back_populates="pantry")

    nombre = Column(String, index=True)
    cantidad_gramos = Column(Float, default=100.0)
    calorias_100g = Column(Float, default=0.0)
    proteinas_100g = Column(Float, default=0.0)
    carbohidratos_100g = Column(Float, default=0.0)
    grasas_100g = Column(Float, default=0.0)
    fecha_registro = Column(String, nullable=True)


class RecetaDB(Base):
    __tablename__ = "recetas"

    id = Column(String, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario = relationship("UsuarioDB", back_populates="recetas")

    nombre = Column(String, index=True)
    descripcion = Column(Text, default="")
    calorias_totales = Column(Float, default=0.0)
    proteinas_totales = Column(Float, default=0.0)
    carbohidratos_totales = Column(Float, default=0.0)
    grasas_totales = Column(Float, default=0.0)
    tiempo_preparacion_min = Column(Integer, default=15)
    utensilios_necesarios = Column(Text, default="Sartén")
    ingredientes = Column(Text, default="[]")


class RegistroConsumoDB(Base):
    __tablename__ = "registros_consumo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    usuario = relationship("UsuarioDB", back_populates="registros")

    fecha = Column(String, index=True)
    nombre = Column(String, index=True)
    calorias = Column(Float, default=0.0)
    proteinas = Column(Float, default=0.0)
    carbohidratos = Column(Float, default=0.0)
    grasas = Column(Float, default=0.0)

class AmistadDB(Base):
    """Solicitud de amistad entre dos usuarios. estado: 'pendiente' o 'aceptada' (una rechazada se borra)."""
    __tablename__ = "amistades"
    __table_args__ = (UniqueConstraint("solicitante_id", "destinatario_id", name="uq_amistad_par"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    solicitante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    destinatario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    estado = Column(String, default="pendiente", nullable=False)
    fecha = Column(String)
