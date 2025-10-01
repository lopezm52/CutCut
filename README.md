# Audio Splitting Microservice

Microservicio en Python para dividir archivos de audio en chunks y devolverlos en base64.

## Características

- ✅ Endpoint POST `/split` con autenticación por API key
- ✅ Soporte para múltiples formatos de audio (mp3, wav, m4a, aac, flac, ogg)
- ✅ Parámetros flexibles para chunk size y overlap
- ✅ Retorna chunks en base64 con metadatos completos
- ✅ Configuración mediante variables de entorno
- ✅ Listo para despliegue con Coolify

## Instalación

### Desarrollo local

```bash
# Clonar el repositorio
git clone <repo-url>
cd CutCut

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores

# Ejecutar
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Con Docker

```bash
docker build -t cutcut .
docker run -p 8000:8000 --env-file .env cutcut
```

## Uso

### Endpoint

```
POST /split?chunk=300s&overlap=5s&format=mp3
```

### Parámetros

- `chunk`: Tamaño del fragmento. Formatos aceptados:
  - `300s` (segundos)
  - `5m` (minutos)
  - `00:05:00` (HH:MM:SS)
  - `300000ms` (milisegundos)

- `overlap` (opcional): Solape entre chunks. Mismo formato que chunk. Default: `5s`

- `format` (opcional): Formato de salida. Default: `mp3`
  - Formatos soportados: mp3, wav, flac, aac, ogg, m4a

### Headers

```
X-API-Key: tu-api-key-aqui
Content-Type: multipart/form-data
```

### Ejemplo de uso

```bash
curl -X POST "http://localhost:8000/split?chunk=300s&overlap=5s&format=mp3" \
  -H "X-API-Key: your-api-key" \
  -F "file=@audio.mp3"
```

### Respuesta

```json
{
  "filename": "audio.mp3",
  "original_duration_ms": 900000,
  "chunk_duration_ms": 300000,
  "overlap_duration_ms": 5000,
  "output_format": "mp3",
  "total_chunks": 3,
  "chunks": [
    {
      "index": 0,
      "start_ms": 0,
      "end_ms": 300000,
      "duration_ms": 300000,
      "mime_type": "audio/mpeg",
      "base64": "SUQzAwAAAAAfdlBSSVYAAAAOAABQZWFr..."
    }
  ]
}
```

## Variables de entorno

```bash
API_KEY=your-secret-api-key
MAX_UPLOAD_MB=100
MAX_CHUNKS=50
```

## Despliegue con Coolify

1. Conecta tu repositorio de GitHub en Coolify
2. Configura las variables de entorno
3. Coolify detectará automáticamente el Dockerfile
4. El servicio estará disponible en el puerto 8000

## Dependencias del sistema

- FFmpeg (incluido en el contenedor Docker)
