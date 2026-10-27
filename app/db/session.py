import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Ruta de la base de datos SQLite en la raíz del proyecto
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nutri_ai.db")

# connect_args={"check_same_thread": False} es necesario para SQLite en entornos multihilo como FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Generador de sesiones de base de datos para FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crea todas las tablas en la base de datos si no existen."""
    import app.db.models  # Importar modelos para registrarlos en el ORM
    Base.metadata.create_all(bind=engine)
    _agregar_columnas_nuevas()


# Columnas añadidas después de crear la BD: create_all no altera tablas existentes
COLUMNAS_NUEVAS = {
    "pantry": {"fecha_registro": "VARCHAR"},
}


def _agregar_columnas_nuevas():
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    with engine.begin() as conn:
        for tabla, columnas in COLUMNAS_NUEVAS.items():
            existentes = {c["name"] for c in inspector.get_columns(tabla)}
            for nombre, tipo in columnas.items():
                if nombre not in existentes:
                    conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))