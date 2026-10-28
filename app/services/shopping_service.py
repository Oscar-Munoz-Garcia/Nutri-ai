import unicodedata
from typing import Dict, List, Optional
from app.models.shopping import SolicitudListaCompra, ListaCompra, ItemListaCompra
import app.services.recipe_service as recipe_service
import app.services.pantry_service as pantry_service


def _normalizar(nombre: str) -> str:
    """Minúsculas y sin tildes para comparar 'Plátano' con 'platano'."""
    sin_tildes = unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode("ascii")
    return " ".join(sin_tildes.lower().split())


def _buscar_en_despensa(nombre_norm: str, despensa: Dict[str, float]) -> Optional[str]:
    """Coincidencia exacta o parcial ('pollo' cubre 'pechuga de pollo' y al revés)."""
    if nombre_norm in despensa:
        return nombre_norm
    candidatos = [n for n in despensa if n and (n in nombre_norm or nombre_norm in n)]
    # Preferimos el nombre más parecido en longitud para evitar falsos positivos
    return min(candidatos, key=lambda n: abs(len(n) - len(nombre_norm))) if candidatos else None


def _leer_despensa(usuario_id: int) -> Dict[str, float]:
    despensa: Dict[str, float] = {}
    for item in pantry_service.obtener_despensa(usuario_id):
        clave = _normalizar(item.nombre)
        despensa[clave] = despensa.get(clave, 0.0) + (item.cantidad_gramos or 0.0)
    return despensa


def generar_lista_compra(solicitud: SolicitudListaCompra, usuario_id: int) -> ListaCompra:
    recetas = {str(r.id): r for r in recipe_service.obtener_todas_las_recetas(usuario_id)}

    necesarios: Dict[str, dict] = {}
    sin_ingredientes: List[str] = []
    no_encontradas: List[str] = []

    for plan in solicitud.recetas:
        receta = recetas.get(str(plan.receta_id))
        if not receta:
            no_encontradas.append(str(plan.receta_id))
            continue
        ingredientes = getattr(receta, "ingredientes", None) or []
        if not ingredientes:
            sin_ingredientes.append(receta.nombre)
            continue
        for ing in ingredientes:
            clave = _normalizar(ing.nombre)
            entrada = necesarios.setdefault(clave, {"nombre": ing.nombre, "gramos": 0.0, "recetas": []})
            entrada["gramos"] += ing.cantidad_gramos * plan.raciones
            if receta.nombre not in entrada["recetas"]:
                entrada["recetas"].append(receta.nombre)

    despensa = _leer_despensa(usuario_id)
    faltantes: List[ItemListaCompra] = []
    cubiertos: List[ItemListaCompra] = []

    for clave, entrada in necesarios.items():
        coincidencia = _buscar_en_despensa(clave, despensa)
        disponible = despensa.get(coincidencia, 0.0) if coincidencia else 0.0
        # Una misma existencia de despensa no puede cubrir dos ingredientes distintos
        if coincidencia:
            despensa[coincidencia] = max(0.0, disponible - entrada["gramos"])

        comprar = max(0.0, entrada["gramos"] - disponible)
        item = ItemListaCompra(
            nombre=entrada["nombre"],
            necesario_g=round(entrada["gramos"], 1),
            disponible_g=round(disponible, 1),
            comprar_g=round(comprar, 1),
            recetas=entrada["recetas"]
        )
        (faltantes if comprar > 0 else cubiertos).append(item)

    faltantes.sort(key=lambda i: i.nombre.lower())
    cubiertos.sort(key=lambda i: i.nombre.lower())

    return ListaCompra(
        faltantes=faltantes,
        cubiertos=cubiertos,
        recetas_sin_ingredientes=sin_ingredientes,
        recetas_no_encontradas=no_encontradas
    )
