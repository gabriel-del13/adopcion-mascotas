import io
import os
from urllib.parse import unquote_plus

import boto3
from PIL import Image, ImageOps

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET_DERIVADAS = os.environ["BUCKET_FOTOS_DERIVADAS"]
TABLA_CATALOGO = os.environ["TABLA_CATALOGO"]

TAMANO_MINIATURA = (400, 400)
TAMANO_FICHA = (1200, 1200)


def procesar_imagen(datos: bytes) -> tuple[bytes, bytes] | None:
    try:
        comprobacion = Image.open(io.BytesIO(datos))
        comprobacion.verify()
    except Exception:
        return None

    imagen = Image.open(io.BytesIO(datos))
    if imagen.mode not in ("RGB", "RGBA"):
        imagen = imagen.convert("RGB")

    miniatura = ImageOps.fit(imagen, TAMANO_MINIATURA)
    buffer_miniatura = io.BytesIO()
    miniatura.save(buffer_miniatura, format="WEBP")

    ficha = imagen.copy()
    ficha.thumbnail(TAMANO_FICHA)
    buffer_ficha = io.BytesIO()
    ficha.save(buffer_ficha, format="WEBP")

    return buffer_miniatura.getvalue(), buffer_ficha.getvalue()


def lambda_handler(event, context):
    for registro in event["Records"]:
        bucket_origen = registro["s3"]["bucket"]["name"]
        key = unquote_plus(registro["s3"]["object"]["key"])

        partes = key.split("/")
        if len(partes) != 4 or partes[0] != "animales":
            print(f"Clave con forma inesperada, se ignora: {key}")
            continue
        _, guarderia_id, animal_id, foto_id = partes

        datos = s3.get_object(Bucket=bucket_origen, Key=key)["Body"].read()
        resultado = procesar_imagen(datos)

        if resultado is None:
            print(f"No es una imagen válida, se borra: {key}")
            s3.delete_object(Bucket=bucket_origen, Key=key)
            continue

        miniatura, ficha = resultado
        clave_base = f"animales/{guarderia_id}/{animal_id}/{foto_id}"
        s3.put_object(Bucket=BUCKET_DERIVADAS, Key=f"{clave_base}-400.webp", Body=miniatura, ContentType="image/webp")
        s3.put_object(Bucket=BUCKET_DERIVADAS, Key=f"{clave_base}-1200.webp", Body=ficha, ContentType="image/webp")

        dynamodb.Table(TABLA_CATALOGO).update_item(
            Key={"PK": f"GUARDERIA#{guarderia_id}", "SK": f"ANIMAL#{animal_id}"},
            UpdateExpression="SET fotos = list_append(if_not_exists(fotos, :vacia), :nueva)",
            ExpressionAttributeValues={":vacia": [], ":nueva": [foto_id]},
        )
