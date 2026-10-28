import httpx
from typing import Optional
from app.models.food import ProductoNutricional

OPENFOODFACTS_API_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"


async def consultar_open_food_facts(codigo_barras: str) -> Optional[ProductoNutricional]:
    """
    Consulta la API pública de Open Food Facts para obtener la información
    nutricional por 100g de un producto a partir de su código de barras.
    """
    codigo_limpio = codigo_barras.strip()
    url = OPENFOODFACTS_API_URL.format(code=codigo_limpio)
    headers = {
        "User-Agent": "NutriAI-App/1.0 (contacto: dev@nutriai.local)"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return None

            data = response.json()
            if data.get("status") != 1 or "product" not in data:
                return None

            product = data["product"]
            nutriments = product.get("nutriments", {})

            calorias = nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal")
            if not calorias:
                # Algunos productos solo publican la energía en kJ
                kj = nutriments.get("energy-kj_100g") or nutriments.get("energy_100g") or 0.0
                calorias = float(kj) / 4.184
            proteinas = nutriments.get("proteins_100g") or nutriments.get("proteins") or 0.0
            carbs = nutriments.get("carbohydrates_100g") or nutriments.get("carbohydrates") or 0.0
            grasas = nutriments.get("fat_100g") or nutriments.get("fat") or 0.0

            nombre_prod = product.get("product_name_es") or product.get("product_name") or "Producto sin nombre"
            marca_prod = product.get("brands") or "Desconocida"
            imagen_prod = product.get("image_front_url") or product.get("image_url")

            return ProductoNutricional(
                codigo_barras=codigo_limpio,
                nombre=nombre_prod,
                marca=marca_prod,
                calorias_100g=round(float(calorias), 1),
                proteinas_100g=round(float(proteinas), 1),
                carbohidratos_100g=round(float(carbs), 1),
                grasas_100g=round(float(grasas), 1),
                imagen_url=imagen_prod
            )
        except Exception:
            return None