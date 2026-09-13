"""Acceso a la tabla `catalogo`: guarderías y animales.

Los modelos de Pydantic usan los mismos nombres de campo que los ítems de
DynamoDB, se traduce algo asi: `model_dump(mode="json")` para
escribir y `Model.model_validate(item)` para leer, añadiendo o ignorando
solo las claves propias de DynamoDB (PK, SK, GSI1PK, GSI1SK).
"""
from boto3.dynamodb.conditions import Attr, Key

from app.core import dynamo
from app.models.animal import Animal, EdadAnimal, EstadoAnimal, TipoAnimal
from app.models.guarderia import EstadoGuarderia, Guarderia


def _animal_a_item(animal: Animal) -> dict:
    item = animal.model_dump(mode="json")
    item["PK"] = f"GUARDERIA#{animal.guarderiaId}"
    item["SK"] = f"ANIMAL#{animal.id}"
    item["GSI1PK"] = f"ESTADO#{animal.estado.value}"
    item["GSI1SK"] = f"TIPO#{animal.tipo.value}#EDAD#{animal.edad.value}"
    return item


def crear_animal(animal: Animal) -> None:
    dynamo.tabla_catalogo.put_item(Item=_animal_a_item(animal))


def listar_animales(
    estado: EstadoAnimal,
    tipo: TipoAnimal | None = None,
    edad: EdadAnimal | None = None,
) -> list[Animal]:
    parametros = {
        "IndexName": "GSI-Catalogo",
        "KeyConditionExpression": Key("GSI1PK").eq(f"ESTADO#{estado.value}"),
    }

    if tipo and edad:
        parametros["KeyConditionExpression"] &= Key("GSI1SK").eq(f"TIPO#{tipo.value}#EDAD#{edad.value}")
    elif tipo:
        parametros["KeyConditionExpression"] &= Key("GSI1SK").begins_with(f"TIPO#{tipo.value}#")
    elif edad:
        parametros["FilterExpression"] = Attr("edad").eq(edad.value)

    respuesta = dynamo.tabla_catalogo.query(**parametros)
    return [Animal.model_validate(item) for item in respuesta["Items"]]


def obtener_animal(animal_id: str) -> Animal | None:
    """Ficha de animal a partir de solo el id.

    # MVP: la PK real es GUARDERIA#<sub>, así que no hay get_item directo con solo el id del animal.
    """
    respuesta = dynamo.tabla_catalogo.scan(
        FilterExpression=Attr("SK").begins_with("ANIMAL#") & Attr("id").eq(animal_id)
    )
    items = respuesta["Items"]
    return Animal.model_validate(items[0]) if items else None


def listar_guarderias_aprobadas() -> list[Guarderia]:
    """
    # MVP: en producción esto lo sirve el catálogo JSON precalculado, no un Scan directo a la tabla en cada petición pública.
    """
    respuesta = dynamo.tabla_catalogo.scan(
        FilterExpression=Attr("SK").eq("METADATA") & Attr("estado").eq(EstadoGuarderia.aprobada.value)
    )
    return [Guarderia.model_validate(item) for item in respuesta["Items"]]