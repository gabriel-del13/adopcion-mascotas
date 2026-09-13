import os
import sys

import boto3
from botocore.exceptions import ClientError

# Credenciales dummy: DynamoDB Local no las valida, pero el SDK de boto3 pide que existan para construir el cliente.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "local")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "local")

REGION = os.environ.get("AWS_REGION", "eu-west-1")
ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
TABLA_CATALOGO = os.environ.get("TABLA_CATALOGO", "adopcion-mascotas-local-catalogo")
TABLA_SOLICITUDES = os.environ.get("TABLA_SOLICITUDES", "adopcion-mascotas-local-solicitudes")

TTL_SOLICITUDES_DIAS = 365  # 12 meses


def cliente_dynamo():
    return boto3.client("dynamodb", region_name=REGION, endpoint_url=ENDPOINT_URL)


def recurso_dynamo():
    return boto3.resource("dynamodb", region_name=REGION, endpoint_url=ENDPOINT_URL)


def crear_tabla_catalogo(client):

    client.create_table(
        TableName=TABLA_CATALOGO,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
            {"AttributeName": "GSI2PK", "AttributeType": "S"},
            {"AttributeName": "GSI2SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                # Catálogo público: PK = ESTADO#<estado>, SK = TIPO#<tipo>#EDAD#<edad>
                "IndexName": "GSI-Catalogo",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                # Panel del admin. Índice disperso: solo las guarderías con estado "pendiente" llevan GSI2PK/GSI2SK.
                "IndexName": "GSI-Guarderias-Pendientes",
                "KeySchema": [
                    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )


def crear_tabla_solicitudes(client):

    client.create_table(
        TableName=TABLA_SOLICITUDES,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
            {"AttributeName": "GSI2PK", "AttributeType": "S"},
            {"AttributeName": "GSI2SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                # Historial del cliente. Índice disperso: solo las solicitudes con cuenta llevan clienteId.
                "IndexName": "GSI-Solicitudes-Por-Cliente",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                # Bandeja de la guardería.
                "IndexName": "GSI-Solicitudes-Por-Guarderia",
                "KeySchema": [
                    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )


def crear_tabla_si_no_existe(client, nombre, funcion_crear):
    try:
        funcion_crear(client)
        print(f"Tabla creada: {nombre}")
    except ClientError as error:
        if error.response["Error"]["Code"] != "ResourceInUseException":
            raise
        print(f"Tabla ya existe, se reutiliza: {nombre}")
    client.get_waiter("table_exists").wait(TableName=nombre)


def activar_ttl_solicitudes(client):
    try:
        client.update_time_to_live(
            TableName=TABLA_SOLICITUDES,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
        )
    except ClientError as error:
        # Ya estaba activado en una ejecución anterior del script.
        if error.response["Error"]["Code"] != "ValidationException":
            raise


def guarderia(sub, nombre, ciudad, provincia, estado, fecha_registro, email, telefono, descripcion):
    item = {
        "PK": f"GUARDERIA#{sub}",
        "SK": "METADATA",
        "sub": sub,
        "nombre": nombre,
        "email": email,
        "telefono": telefono,
        "ciudad": ciudad,
        "provincia": provincia,
        "estado": estado,
        "fechaRegistro": fecha_registro,
        "descripcion": descripcion,
    }
    if estado == "pendiente":
        item["GSI2PK"] = "PENDIENTE"
        item["GSI2SK"] = f"FECHA#{fecha_registro}"
    return item


def animal(id_animal, guarderia_sub, nombre, tipo, edad, estado, ciudad, provincia, descripcion):
    return {
        "PK": f"GUARDERIA#{guarderia_sub}",
        "SK": f"ANIMAL#{id_animal}",
        "id": id_animal,
        "guarderiaId": guarderia_sub,
        "nombre": nombre,
        "tipo": tipo,
        "edad": edad,
        "estado": estado,
        "ciudad": ciudad,
        "provincia": provincia,
        "descripcion": descripcion,
        # MVP: URLs de ejemplo. En producción son presignadas hacia S3 (la carpeta de thumbs)
        "fotos": [f"https://ejemplo.com/fotos/{id_animal}-1.jpg"],
        "fechaPublicacion": "2026-01-15",
        "GSI1PK": f"ESTADO#{estado}",
        "GSI1SK": f"TIPO#{tipo}#EDAD#{edad}",
    }


def cliente(sub, nombre, email, telefono, fecha_registro):
    return {
        "PK": f"CLIENTE#{sub}",
        "SK": "METADATA",
        "sub": sub,
        "nombre": nombre,
        "email": email,
        "telefono": telefono,
        "fechaRegistro": fecha_registro,
    }


def datos_de_prueba():
    guarderias = [
        guarderia(
            "g1", "Protectora Huellas Felices", "Madrid", "Madrid", "aprobada",
            "2025-11-03", "contacto@huellasfelices.example", "600111222",
            "Protectora sin ánimo de lucro centrada en perros abandonados.",
        ),
        guarderia(
            "g2", "Refugio Segunda Oportunidad", "Valencia", "Valencia", "aprobada",
            "2025-12-10", "contacto@segundaoportunidad.example", "600333444",
            "Guardería especializada en gatos y animales de edad avanzada.",
        ),
        guarderia(
            "g3", "Asociación Patitas de Panama", "Sevilla", "Sevilla", "pendiente",
            "2026-09-01", "contacto@patitasdepanama.example", "600555666",
            "Solicitud de alta reciente, todavía sin aprobar por el administrador.",
        ),
    ]

    animales_g1 = [
        animal("a1", "g1", "Rex", "perro", "adulto", "disponible", "Madrid", "Madrid", "Cruce de pastor alemán, muy sociable."),
        animal("a2", "g1", "Lobita", "perro", "cachorro", "disponible", "Madrid", "Madrid", "Cachorra rescatada de una camada abandonada."),
        animal("a3", "g1", "Toby", "perro", "senior", "disponible", "Madrid", "Madrid", "Tranquilo, ideal para piso."),
        animal("a4", "g1", "Corona", "perro", "joven", "en_proceso", "Madrid", "Madrid", "En trámites de adopción con una familia."),
        animal("a5", "g1", "Coco", "perro", "adulto", "disponible", "Getafe", "Madrid", "Le encanta el agua y jugar con otros perros."),
    ]
    animales_g2 = [
        animal("a6", "g2", "Mia", "gato", "adulto", "disponible", "Valencia", "Valencia", "Independiente, esterilizada y vacunada."),
        animal("a7", "g2", "Simba", "gato", "cachorro", "disponible", "Valencia", "Valencia", "Muy juguetón, se lleva bien con niños."),
        animal("a8", "g2", "Bigotes", "gato", "senior", "disponible", "Valencia", "Valencia", "Necesita cuidados por artrosis leve."),
        animal("a9", "g2", "Mini", "gato", "joven", "adoptado", "Gandía", "Valencia", "Adoptada en enero de 2026."),
        animal("a10", "g2", "Michi", "gato", "adulto", "disponible", "Sagunto", "Valencia", "Convive bien con otros gatos."),
    ]

    clientes = [
        cliente("c1", "Marcos Abad", "marcos.abad@ejemplo.com", "611222333", "2026-02-14"),
        cliente("c2", "Sergio Ciro", "sergio.ciro@ejemplo.com", "622333444", "2026-03-20"),
    ]

    return guarderias, animales_g1 + animales_g2, clientes


def sembrar_datos(resource):
    guarderias, animales, clientes = datos_de_prueba()

    tabla_catalogo = resource.Table(TABLA_CATALOGO)
    with tabla_catalogo.batch_writer() as batch:
        for item in guarderias + animales:
            batch.put_item(Item=item)

    tabla_solicitudes = resource.Table(TABLA_SOLICITUDES)
    with tabla_solicitudes.batch_writer() as batch:
        for item in clientes:
            batch.put_item(Item=item)

    print(f"Sembrado: {len(guarderias)} guarderías, {len(animales)} animales, {len(clientes)} clientes.")


def main():
    client = cliente_dynamo()
    crear_tabla_si_no_existe(client, TABLA_CATALOGO, crear_tabla_catalogo)
    crear_tabla_si_no_existe(client, TABLA_SOLICITUDES, crear_tabla_solicitudes)
    activar_ttl_solicitudes(client)
    sembrar_datos(recurso_dynamo())


if __name__ == "__main__":
    try:
        main()
    except ClientError as error:
        print(f"Error de DynamoDB: {error}", file=sys.stderr)
        sys.exit(1)
