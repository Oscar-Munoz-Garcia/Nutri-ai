from sqlalchemy import inspect, text

# Columnas añadidas después de la creación inicial de las tablas.
# create_all() no altera tablas existentes, así que se añaden aquí con ALTER TABLE idempotente.
COLUMNAS_NUEVAS = {
    "pantry": {"fecha_registro": "VARCHAR"},
    "recetas": {"ingredientes": "TEXT DEFAULT '[]'"},
}

# Tablas cuyos datos pertenecen a un usuario concreto
TABLAS_POR_USUARIO = ["pantry", "recetas", "registros_consumo", "peso_historial"]


def _anadir_columnas_faltantes(conn) -> None:
    inspector = inspect(conn)
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        if not inspector.has_table(tabla):
            continue
        existentes = {c["name"] for c in inspector.get_columns(tabla)}
        for nombre, tipo in columnas.items():
            if nombre not in existentes:
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))


def _asignar_filas_huerfanas(conn) -> None:
    """Las filas creadas antes del modo multiusuario no tienen usuario_id.
    Se asignan al primer usuario registrado para que no queden visibles para todos ni se pierdan."""
    primer_usuario = conn.execute(text("SELECT MIN(id) FROM usuarios")).scalar()
    if primer_usuario is None:
        return
    for tabla in TABLAS_POR_USUARIO:
        conn.execute(
            text(f"UPDATE {tabla} SET usuario_id = :uid WHERE usuario_id IS NULL"),
            {"uid": primer_usuario}
        )


def aplicar_migraciones(engine) -> None:
    with engine.begin() as conn:
        _anadir_columnas_faltantes(conn)
        _asignar_filas_huerfanas(conn)
