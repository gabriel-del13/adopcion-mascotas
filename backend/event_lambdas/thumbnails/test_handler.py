"""Test de la función pura de procesado de imagen, sin AWS.

Requiere Pillow instalado (no forma parte de backend/api/requirements*.txt).
"""
import io
import os

os.environ.setdefault("BUCKET_FOTOS_DERIVADAS", "bucket-de-prueba")
os.environ.setdefault("TABLA_CATALOGO", "tabla-de-prueba")

from PIL import Image  # noqa: E402

from handler import procesar_imagen  # noqa: E402


def _png_en_memoria(ancho: int = 800, alto: int = 600) -> bytes:
    imagen = Image.new("RGB", (ancho, alto), color=(120, 200, 40))
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def test_imagen_valida_genera_dos_derivadas_webp_mas_pequenas():
    original = _png_en_memoria()
    resultado = procesar_imagen(original)

    assert resultado is not None
    miniatura, ficha = resultado
    assert len(miniatura) < len(original)
    assert len(ficha) < len(original)

    imagen_miniatura = Image.open(io.BytesIO(miniatura))
    assert imagen_miniatura.format == "WEBP"
    assert imagen_miniatura.size == (400, 400)

    imagen_ficha = Image.open(io.BytesIO(ficha))
    assert imagen_ficha.format == "WEBP"
    assert max(imagen_ficha.size) <= 1200


def test_imagen_horizontal_conserva_aspecto_en_la_ficha_no_en_la_miniatura():
    original = _png_en_memoria(ancho=2400, alto=1200)
    miniatura, ficha = procesar_imagen(original)

    assert Image.open(io.BytesIO(miniatura)).size == (400, 400)
    ancho_ficha, alto_ficha = Image.open(io.BytesIO(ficha)).size
    assert ancho_ficha == 1200
    assert alto_ficha == 600  # mismo aspect ratio 2:1 que el original


def test_datos_que_no_son_una_imagen_devuelven_none():
    assert procesar_imagen(b"esto no es una imagen, es texto plano") is None


def test_content_type_mentiroso_no_engana_a_pillow():
    """Un .txt renombrado a .jpg (o con Content-Type falso) sigue sin ser una
    imagen real cuando Pillow lo abre de verdad — el escenario exacto que
    justifica no confiar en el Content-Type declarado en la presignada."""
    datos_falsos = b"contenido de texto plano que alguien llamo foto.jpg"
    assert procesar_imagen(datos_falsos) is None
