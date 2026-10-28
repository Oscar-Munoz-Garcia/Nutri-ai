from sqlalchemy import inspect, text

# Columnas añadidas después de la creación inicial de las tablas.
# create_all() no altera tablas existentes, así que se añaden aquí con ALTER TABLE idempotente.
COLUMNAS_NUEVAS = {
    "pantry": {"fecha_registro": "VARCHAR"},
    "recetas": {"ingredientes": "TEXT DEFAULT '[]'", "pasos": "TEXT DEFAULT '[]'"},
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


def _migracion_aplicada(conn, nombre: str) -> bool:
    conn.execute(text("CREATE TABLE IF NOT EXISTS migraciones_aplicadas (nombre VARCHAR PRIMARY KEY)"))
    return conn.execute(
        text("SELECT 1 FROM migraciones_aplicadas WHERE nombre = :n"), {"n": nombre}
    ).first() is not None


def _marcar_migracion(conn, nombre: str) -> None:
    conn.execute(text("INSERT INTO migraciones_aplicadas (nombre) VALUES (:n)"), {"n": nombre})


def _asignar_filas_huerfanas(conn) -> None:
    """Migración de UNA SOLA VEZ: las filas creadas antes del modo multiusuario no tienen usuario_id
    y se asignan al primer usuario registrado (el único que usaba la app entonces).
    Queda registrada en migraciones_aplicadas, así que una fila sin dueño que aparezca más adelante
    nunca se asigna a nadie: queda invisible para todos."""
    nombre = "asignar_filas_huerfanas_v1"
    if _migracion_aplicada(conn, nombre):
        return

    primer_usuario = conn.execute(text("SELECT MIN(id) FROM usuarios")).scalar()
    if primer_usuario is None:
        hay_huerfanas = any(
            conn.execute(text(f"SELECT 1 FROM {tabla} WHERE usuario_id IS NULL LIMIT 1")).first()
            for tabla in TABLAS_POR_USUARIO
        )
        if hay_huerfanas:
            return  # Datos antiguos sin ningún usuario aún: se asignarán al primero que se registre
    else:
        for tabla in TABLAS_POR_USUARIO:
            conn.execute(
                text(f"UPDATE {tabla} SET usuario_id = :uid WHERE usuario_id IS NULL"),
                {"uid": primer_usuario}
            )
    _marcar_migracion(conn, nombre)


def aplicar_migraciones(engine) -> None:
    with engine.begin() as conn:
        _anadir_columnas_faltantes(conn)
        _asignar_filas_huerfanas(conn)
