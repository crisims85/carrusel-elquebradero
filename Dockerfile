FROM python:3.12-slim
RUN apt-get update && apt-get install -y fonts-liberation && rm -rf /var/lib/apt/lists/*
RUN pip install pillow requests flask
WORKDIR /app
RUN mkdir -p /app/output
COPY generar_carrusel.py /app/generar_carrusel.py
COPY api.py /app/api.py
CMD ["python3", "/app/api.py"]
