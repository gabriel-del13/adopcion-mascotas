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
    respuesta = dynamo.tabla_catalogo.scan(
        FilterExpression=Attr("SK").begins_with("ANIMAL#") & Attr("id").eq(animal_id)
    )
    items = respuesta["Items"]
    return Animal.model_validate(items[0]) if items else None


def obtener_guarderia(sub: str) -> Guarderia | None:
    respuesta = dynamo.tabla_catalogo.get_item(Key={"PK": f"GUARDERIA#{sub}", "SK": "METADATA"})
    item = respuesta.get("Item")
    return Guarderia.model_validate(item) if item else None


def listar_guarderias_aprobadas() -> list[Guarderia]:
    respuesta = dynamo.tabla_catalogo.scan(
        FilterExpression=Attr("SK").eq("METADATA") & Attr("estado").eq(EstadoGuarderia.aprobada.value)
    )
    return [Guarderia.model_validate(item) for item in respuesta["Items"]]


def listar_guarderias_pendientes() -> list[Guarderia]:
    respuesta = dynamo.tabla_catalogo.query(
        IndexName="GSI-Guarderias-Pendientes",
        KeyConditionExpression=Key("GSI2PK").eq("PENDIENTE"),
    )
    return [Guarderia.model_validate(item) for item in respuesta["Items"]]


def aprobar_guarderia(sub: str) -> None:
    dynamo.tabla_catalogo.update_item(
        Key={"PK": f"GUARDERIA#{sub}", "SK": "METADATA"},
        UpdateExpression="SET estado = :estado REMOVE GSI2PK, GSI2SK, motivoRechazo",
        ExpressionAttributeValues={":estado": EstadoGuarderia.aprobada.value},
    )


def rechazar_guarderia(sub: str, motivo: str) -> None:
    dynamo.tabla_catalogo.update_item(
        Key={"PK": f"GUARDERIA#{sub}", "SK": "METADATA"},
        UpdateExpression="SET estado = :estado, motivoRechazo = :motivo REMOVE GSI2PK, GSI2SK",
        ExpressionAttributeValues={
            ":estado": EstadoGuarderia.rechazada.value,
            ":motivo": motivo,
        },
    )


def crear_guarderia(guarderia: Guarderia) -> None:
    item = guarderia.model_dump(mode="json", exclude_none=True)
    item["PK"] = f"GUARDERIA#{guarderia.sub}"
    item["SK"] = "METADATA"
    if guarderia.estado == EstadoGuarderia.pendiente:
        item["GSI2PK"] = "PENDIENTE"
        item["GSI2SK"] = f"FECHA#{guarderia.fechaRegistro.isoformat()}"
    dynamo.tabla_catalogo.put_item(Item=item)


def actualizar_perfil_guarderia(sub: str, nombre: str, telefono: str, ciudad: str, provincia: str, descripcion: str) -> None:
    dynamo.tabla_catalogo.update_item(
        Key={"PK": f"GUARDERIA#{sub}", "SK": "METADATA"},
        UpdateExpression="SET nombre = :nombre, telefono = :telefono, ciudad = :ciudad, provincia = :provincia, descripcion = :descripcion",
        ExpressionAttributeValues={
            ":nombre": nombre,
            ":telefono": telefono,
            ":ciudad": ciudad,
            ":provincia": provincia,
            ":descripcion": descripcion,
        },
    )


def obtener_animal_de_guarderia(guarderia_id: str, animal_id: str) -> Animal | None:
    respuesta = dynamo.tabla_catalogo.get_item(Key={"PK": f"GUARDERIA#{guarderia_id}", "SK": f"ANIMAL#{animal_id}"})
    item = respuesta.get("Item")
    return Animal.model_validate(item) if item else None


def actualizar_animal(animal: Animal) -> None:
    dynamo.tabla_catalogo.put_item(Item=_animal_a_item(animal))


def eliminar_animal(guarderia_id: str, animal_id: str) -> None:
    dynamo.tabla_catalogo.delete_item(Key={"PK": f"GUARDERIA#{guarderia_id}", "SK": f"ANIMAL#{animal_id}"})


def marcar_estado_animal(guarderia_id: str, animal_id: str, estado: EstadoAnimal) -> None:
    dynamo.tabla_catalogo.update_item(
        Key={"PK": f"GUARDERIA#{guarderia_id}", "SK": f"ANIMAL#{animal_id}"},
        UpdateExpression="SET estado = :estado, GSI1PK = :gsi1pk",
        ExpressionAttributeValues={":estado": estado.value, ":gsi1pk": f"ESTADO#{estado.value}"},
    )


def incrementar_contador_rechazos(guarderia_id: str, animal_id: str) -> None:
    dynamo.tabla_catalogo.update_item(
        Key={"PK": f"GUARDERIA#{guarderia_id}", "SK": f"ANIMAL#{animal_id}"},
        UpdateExpression="ADD contadorRechazosAnonimos :uno",
        ExpressionAttributeValues={":uno": 1},
    )