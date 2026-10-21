from sqlalchemy import Column, String, Float, Integer, Text, Date
from datetime import date
from app.db.session import Base


class PerfilDB(Base):
    __tablename__ = "perfil"

    id = Column(Integer, primary_key=True, index=True, default=1)
    nombre = Column(String, default="Oscar")
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
    fecha = Column(String, index=True)  # YYYY-MM-DD
    peso_kg = Column(Float)


class PantryDB(Base):
    __tablename__ = "pantry"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, index=True)
    cantidad_gramos = Column(Float, default=100.0)
    calorias_100g = Column(Float, default=0.0)
    proteinas_100g = Column(Float, default=0.0)
    carbohidratos_100g = Column(Float, default=0.0)
    grasas_100g = Column(Float, default=0.0)


class RecetaDB(Base):
    __tablename__ = "recetas"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, index=True)
    descripcion = Column(Text, default="")
    calorias_totales = Column(Float, default=0.0)
    proteinas_totales = Column(Float, default=0.0)
    carbohidratos_totales = Column(Float, default=0.0)
    grasas_totales = Column(Float, default=0.0)
    tiempo_preparacion_min = Column(Integer, default=15)
    utensilios_necesarios = Column(Text, default="Sartén")


class RegistroConsumoDB(Base):
    __tablename__ = "registros_consumo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(String, index=True)  # Formato: YYYY-MM-DD
    nombre = Column(String, index=True)
    calorias = Column(Float, default=0.0)
    proteinas = Column(Float, default=0.0)
    carbohidratos = Column(Float, default=0.0)
    grasas = Column(Float, default=0.0)