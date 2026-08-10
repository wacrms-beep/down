FROM python:3.11-slim

# ffmpeg est un binaire système : pip ne peut pas l'installer,
# il faut passer par le gestionnaire de paquets de l'OS.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Render fournit le port via la variable d'env $PORT
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
