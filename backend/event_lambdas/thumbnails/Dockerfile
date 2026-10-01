# Imagen de contenedor, no zip: Pillow lleva binarios nativos y empaquetarlo
# en zip implica pelearse con wheels de manylinux para ARM64. Como esta
# Lambda es asíncrona (disparada por S3, nadie espera la respuesta), el
# arranque en frío algo mayor de una imagen no importa.
FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY handler.py .

CMD ["handler.lambda_handler"]
