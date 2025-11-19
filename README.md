# Audio Splitting Microservice

Microservicio en Python para dividir archivos de audio en chunks y devolverlos en base64.

## Características

- ✅ Endpoint POST `/split` con autenticación por API key
- ✅ Soporte para múltiples formatos de audio (entrada y salida)
- ✅ Detección automática del formato de entrada
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
uvicorn app:app --reload --host 0.0.0.0 --port 3000
```

### Con Docker

```bash
docker build -t cutcut .
docker run -p 3005:3000 --env-file .env cutcut
```

## Uso

### Endpoint Principal

```
POST /split?chunk=300s&overlap=5s&format=mp3
```

### Health Check

```
GET /health
```

### Parámetros

#### `chunk` (requerido)
Tamaño del fragmento. Formatos aceptados:
- `300s` - 300 segundos
- `5m` - 5 minutos
- `00:05:00` - formato HH:MM:SS
- `300000ms` - 300,000 milisegundos

#### `overlap` (opcional)
Solape entre chunks. Mismo formato que `chunk`.
- **Default:** `5s`
- **Ejemplo:** `10s`, `0.5m`, `00:00:10`

#### `format` (opcional)
Formato de salida del audio.
- **Default:** `mp3`
- **Soportados:** `mp3`, `wav`, `m4a`, `aac`, `flac`, `ogg`

**Nota:** El formato de entrada se detecta automáticamente. Puedes subir cualquier formato que FFmpeg soporte y convertirlo al formato de salida deseado.

### Headers Requeridos

```
X-API-Key: tu-api-key-aqui
Content-Type: multipart/form-data
```

### Body

```
Key: file
Type: Binary/File
Value: [Tu archivo de audio]
```

### Ejemplo de uso con cURL

```bash
# Entrada M4A → Salida MP3
curl -X POST "http://localhost:3005/split?chunk=5m&overlap=10s&format=mp3" \
  -H "X-API-Key: your-api-key" \
  -F "file=@podcast.m4a"

# Entrada WAV → Salida M4A
curl -X POST "http://localhost:8000/split?chunk=300s&format=m4a" \
  -H "X-API-Key: your-api-key" \
  -F "file=@recording.wav"

# Health check
curl http://localhost:8000/health
```

### Ejemplo de uso con n8n

**HTTP Request Node:**
```
Method: POST
URL: https://cutcut.besserich.com/split

Query Parameters:
  chunk: 5m
  overlap: 5s
  format: mp3

Headers:
  X-API-Key: your-api-key

Body:
  Type: Form-Data
  Parameters:
    Key: file
    Type: Binary Data
    Value: $binary.data

Options:
  Timeout: 600000  (10 minutos para archivos grandes)
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

## Variables de Entorno

```bash
# Requeridas
API_KEY=your-secret-api-key-here

# Opcionales (con valores por defecto)
MAX_UPLOAD_MB=100    # Tamaño máximo del archivo (MB)
MAX_CHUNKS=50        # Número máximo de chunks por petición
```

## Formatos Soportados

### Entrada (Auto-detectado)
Cualquier formato que FFmpeg pueda leer:
- `mp3`, `wav`, `m4a`, `aac`, `flac`, `ogg`
- `wma`, `opus`, `webm`, `mp4` (audio)
- Y muchos más...

### Salida (Parámetro `format`)
- `mp3` - MPEG Audio Layer 3
- `wav` - Waveform Audio
- `m4a` - MPEG-4 Audio (usa contenedor MP4)
- `aac` - Advanced Audio Coding
- `flac` - Free Lossless Audio Codec
- `ogg` - Ogg Vorbis

## Monitoreo

### Ver logs en tiempo real

```bash
# Encontrar el contenedor
docker ps | grep cutcut

# Ver logs
docker logs -f <container-id>

# Ver últimos 100 logs
docker logs --tail 100 <container-id>

# Buscar errores
docker logs <container-id> 2>&1 | grep -i "error\|killed\|memory"
```

### Ver uso de recursos

```bash
# Uso actual
docker stats --no-stream <container-id>

# En tiempo real
docker stats <container-id>

# Configuración de memoria
docker inspect <container-id> | grep -i memory
```

### Ver archivos temporales

```bash
# Entrar al contenedor
docker exec -it <container-id> bash

# Ver archivos en /tmp
ls -lh /tmp/
du -sh /tmp/

# Limpiar archivos antiguos (si es necesario)
find /tmp -name "tmp*" -mtime +1 -delete
```

### Verificar salud del servicio

```bash
# Health check local
curl http://localhost:8000/health

# Health check remoto
curl https://cutcut.besserich.com/health
```

## Despliegue con Coolify

1. **Conecta tu repositorio** de GitHub en Coolify
2. **Build Pack:** Coolify detectará automáticamente el Dockerfile
3. **Configura variables de entorno:**
   ```
   API_KEY=tu-api-key-secreta
   MAX_UPLOAD_MB=100
   MAX_CHUNKS=50
   ```
4. **Port:** 8000 (auto-detectado del Dockerfile)
5. **Domain:** Configura tu dominio personalizado
6. **Deploy:** El servicio estará listo en minutos

### Límites de Recursos (Opcional)

Si experimentas problemas de memoria, puedes configurar límites en Coolify:

```
Advanced → Resource Limits:
  Maximum Memory Limit: 1024  (1GB recomendado)
  Maximum Swap Limit: 0       (sin límite de swap)
```

**Nota:** Para la mayoría de casos, no es necesario configurar límites. El servicio gestiona la memoria eficientemente limpiando archivos temporales después de cada petición.

### Troubleshooting

#### Error 502 - Bad Gateway
- Verifica que el contenedor esté corriendo: `docker ps | grep cutcut`
- Revisa los logs: `docker logs <container-id>`
- Verifica el health check: `curl http://localhost:8000/health`

#### Archivo demasiado grande
- Aumenta `MAX_UPLOAD_MB` en variables de entorno
- Considera dividir el archivo antes de procesarlo
- Aumenta el timeout en el cliente (n8n: 600000ms = 10 min)

#### Demasiados chunks generados
- Reduce `MAX_CHUNKS` o aumenta el tamaño del `chunk`
- Para un audio de 2 horas con chunks de 5 min: 24 chunks

#### Error de formato M4A
- Ya está corregido en la versión actual
- M4A usa contenedor MP4 internamente en FFmpeg

## Arquitectura

```
Cliente (n8n/curl)
    ↓
Traefik Proxy
    ↓
FastAPI (Python 3.12)
    ↓
Pydub + FFmpeg
    ↓
Chunks en Base64
```

## Dependencias del Sistema

- Python 3.12
- FFmpeg (incluido en el contenedor Docker)
- Dependencias Python: ver `requirements.txt`

## Desarrollo

### Ejecutar tests

```bash
# TODO: Agregar tests
pytest
```

### Actualizar dependencias

```bash
pip install --upgrade -r requirements.txt
pip freeze > requirements.txt
```

### Hacer cambios

```bash
git add .
git commit -m "Descripción del cambio"
git push origin main
```

Coolify detectará los cambios automáticamente y redesplegará el servicio.

## Actualizaciones Recientes (Nov 2025)

- **Cambio de Puerto:** El servicio ahora corre internamente en el puerto `3000` y se expone en el `3005` (Docker).
- **Optimización de Rendimiento:** Refactorización para usar `run_in_threadpool`, evitando el bloqueo del event loop durante el procesamiento de audio pesado.
- **Seguridad:** Implementación de `secrets.compare_digest` para la validación de API Key (protección contra timing attacks).
- **Correcciones:** Solucionado bucle infinito en la lógica de chunking y mejorado el soporte para archivos M4A.

## Licencia

MIT

## Soporte

Para reportar problemas o sugerencias, abre un issue en GitHub.
