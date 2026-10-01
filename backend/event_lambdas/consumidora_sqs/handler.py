"""Lambda consumidora de la cola de notificaciones, disparada por SQS.
"""
import json
import os
from html import escape

import boto3

ses = boto3.client("ses")

EMAIL_REMITENTE = os.environ["EMAIL_REMITENTE"]


def _cuerpo_html(mensaje: dict) -> str:
    # Todo lo que viene del formulario público (anónimo, sin autenticar) se
    # escapa antes de insertarse en el HTML del correo.
    situacion = (
        f"<p><strong>Situación del adoptante:</strong> {escape(mensaje['descripcionSituacion'])}</p>"
        if mensaje.get("descripcionSituacion")
        else ""
    )
    cuenta = " (usuario con cuenta y correo verificado)" if mensaje.get("esClienteConCuenta") else ""
    return f"""
    <p>Nueva solicitud de adopción para <strong>{escape(mensaje['animalNombre'])}</strong>
    ({escape(mensaje['animalTipo'])}, {escape(mensaje['animalEdad'])}).</p>
    <p><strong>Adoptante:</strong> {escape(mensaje['adoptanteNombre'])}{cuenta}<br>
    <strong>Email:</strong> {escape(mensaje['adoptanteEmail'])}<br>
    <strong>Teléfono:</strong> {escape(mensaje['adoptanteTelefono'])}</p>
    <p><strong>Mensaje:</strong> {escape(mensaje['mensaje'])}</p>
    {situacion}
    <p>
      <a href="{mensaje['enlaceAceptar']}">Aceptar solicitud</a> &nbsp;|&nbsp;
      <a href="{mensaje['enlaceRechazar']}">Rechazar solicitud</a>
    </p>
    <p>También puedes gestionarla desde tu panel.</p>
    """


def _cuerpo_texto(mensaje: dict) -> str:
    return (
        f"Nueva solicitud de adopción para {mensaje['animalNombre']} "
        f"({mensaje['animalTipo']}, {mensaje['animalEdad']}).\n\n"
        f"Adoptante: {mensaje['adoptanteNombre']}\n"
        f"Email: {mensaje['adoptanteEmail']}\n"
        f"Teléfono: {mensaje['adoptanteTelefono']}\n"
        f"Mensaje: {mensaje['mensaje']}\n\n"
        f"Aceptar: {mensaje['enlaceAceptar']}\n"
        f"Rechazar: {mensaje['enlaceRechazar']}\n"
    )


def _procesar_nueva_solicitud(mensaje: dict) -> None:
    ses.send_email(
        Source=EMAIL_REMITENTE,
        Destination={"ToAddresses": [mensaje["guarderiaEmail"]]},
        Message={
            "Subject": {"Data": f"Nueva solicitud de adopción para {mensaje['animalNombre']}"},
            "Body": {
                "Html": {"Data": _cuerpo_html(mensaje)},
                "Text": {"Data": _cuerpo_texto(mensaje)},
            },
        },
    )


def lambda_handler(event, context):
    for registro in event["Records"]:
        mensaje = json.loads(registro["body"])
        if mensaje["tipo"] == "nueva_solicitud":
            _procesar_nueva_solicitud(mensaje)
        else:
            raise ValueError(f"Tipo de mensaje desconocido: {mensaje['tipo']!r}")
