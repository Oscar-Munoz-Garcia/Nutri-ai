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
    planes = relationship("PlanNutricionDB", cascade="all, delete-orphan")
    planes_por_fecha = relationship("PlanFechaDB", cascade="all, delete-orphan")
    dias_libres = relationship("DiaLibreDB", cascade="all, delete-orphan")


class PerfilDB(Base):
    __tablename__ = "perfil"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, unique=True)
    usuario = relationship("UsuarioDB", back_populates="perfil")

    nombre = Column(String, default="Usuario")
    apellidos = Column(String, default="")
    objetivo = Column(String, default="mantenimiento")
    # 0 hasta que el usuario nuevo rellena el cuestionario de alta
    registro_completo = Column(Integer, default=0)
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
    # Cuántos días libres (comidas fuera) se permite marcar por semana
    dias_libres_semana = Column(Integer, default=1)

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
    pasos = Column(Text, default="[]")


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
    # Comida del plan a la que pertenece (Desayuno, Cena...) y gramos, si se añadió por peso
    comida = Column(String, nullable=True)
    gramos = Column(Float, nullable=True)

class AmistadDB(Base):
    """Solicitud de amistad entre dos usuarios. estado: 'pendiente' o 'aceptada' (una rechazada se borra)."""
    __tablename__ = "amistades"
    __table_args__ = (UniqueConstraint("solicitante_id", "destinatario_id", name="uq_amistad_par"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    solicitante_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    destinatario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    estado = Column(String, default="pendiente", nullable=False)
    fecha = Column(String)


class PlanNutricionDB(Base):
    """Plan de nutrición del usuario (p. ej. «Entrenamiento» 2300 kcal, «Descanso» 2000 kcal).
    El plan principal refleja los objetivos del perfil y se usa los días sin plan asignado."""
    __tablename__ = "planes_nutricion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nombre = Column(String, nullable=False)
    es_principal = Column(Integer, default=0)
    # Días de la semana en los que se aplica: "0,2,4" (0 = lunes ... 6 = domingo)
    dias_semana = Column(String, default="")

    calorias_objetivo = Column(Float, default=2200.0)
    proteinas_objetivo = Column(Float, default=160.0)
    carbohidratos_objetivo = Column(Float, default=210.0)
    grasas_objetivo = Column(Float, default=70.0)
    # Comidas del día en este plan, en orden: JSON '["Desayuno", "Comida", "Cena"]'
    comidas = Column(Text, nullable=True)


class PlanFechaDB(Base):
    """Cambio puntual: en esta fecha se usa este plan en lugar del que toca por día de la semana."""
    __tablename__ = "planes_por_fecha"
    __table_args__ = (UniqueConstraint("usuario_id", "fecha", name="uq_plan_fecha"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    fecha = Column(String, nullable=False)
    plan_id = Column(Integer, ForeignKey("planes_nutricion.id"), nullable=False)


class DiaLibreDB(Base):
    """Día libre (comida fuera): no cuenta para las metas ni rompe la racha."""
    __tablename__ = "dias_libres"
    __table_args__ = (UniqueConstraint("usuario_id", "fecha", name="uq_dia_libre"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    fecha = Column(String, nullable=False)
