FROM python:3.11-slim

# Instalar FFmpeg y dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear directorio para archivos temporales
RUN mkdir -p /tmp/audio

# Exponer puerto
EXPOSE 8000

# Configurar variables de entorno por defecto
ENV API_KEY=your-secret-api-key-here
ENV MAX_UPLOAD_MB=100
ENV MAX_CHUNKS=50

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
