"""Empaqueta un directorio en un zip con separadores '/' en los nombres de
entrada, aunque se genere en Windows: Lambda espera rutas estilo Unix dentro
del zip.

Uso: python zip_dir.py <directorio_origen> <zip_destino>
"""
import sys
import zipfile
from pathlib import Path

origen = Path(sys.argv[1])
destino = sys.argv[2]

with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
    for ruta in sorted(origen.rglob("*")):
        if ruta.is_file():
            zf.write(ruta, ruta.relative_to(origen).as_posix())
