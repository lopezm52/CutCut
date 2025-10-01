# 🎵 CutCut - Microservicio de División de Audio

## ✅ Proyecto Completado

**Microservicio en Python** para dividir archivos de audio en chunks y devolverlos en base64, listo para despliegue en **Coolify**.

---

## 🏗️ Arquitectura

```
CutCut/
├── 📱 API FastAPI (app.py)
├── 🐳 Docker & Compose
├── ☁️  Configuración Coolify
├── 🧪 Scripts de prueba
├── 📚 Documentación completa
└── 🔄 CI/CD GitHub Actions
```

---

## 🚀 Características Implementadas

### ✅ API REST
- **Endpoint**: `POST /split`
- **Autenticación**: API Key via header `X-API-Key`
- **Formatos**: mp3, wav, m4a, aac, flac, ogg
- **Parámetros flexibles**: chunk, overlap, format

### ✅ Procesamiento de Audio
- **Biblioteca**: pydub + FFmpeg
- **Formatos de tiempo**: 300s, 5m, 00:05:00, 300000ms
- **Overlap**: Solapamiento configurable entre chunks
- **Base64**: Retorna chunks codificados

### ✅ Configuración Robusta
- **Variables de entorno**: API_KEY, MAX_UPLOAD_MB, MAX_CHUNKS
- **Límites configurables**: Protección contra archivos grandes
- **Health checks**: Endpoints `/health` y `/`

### ✅ Despliegue
- **Docker**: Dockerfile optimizado con FFmpeg
- **Docker Compose**: Configuración completa
- **Coolify**: Documentación específica
- **CI/CD**: GitHub Actions para testing

### ✅ Documentación
- **README.md**: Guía completa de instalación y uso
- **examples.md**: Ejemplos prácticos con curl
- **Scripts**: setup.sh y test_service.sh

---

## 🛠️ Tecnologías Utilizadas

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Python** | 3.11+ | Runtime principal |
| **FastAPI** | 0.115.0 | Framework API REST |
| **pydub** | 0.25.1 | Procesamiento de audio |
| **FFmpeg** | Latest | Conversión de formatos |
| **Docker** | Latest | Containerización |
| **Uvicorn** | 0.31.0 | Servidor ASGI |

---

## 📋 Casos de Uso

1. **Podcasts**: Dividir episodios largos en segmentos
2. **Música**: Crear previews o samples
3. **Conferencias**: Segmentar presentaciones
4. **Audiolibros**: Crear capítulos
5. **Streaming**: Preparar contenido para HLS/DASH

---

## 🔧 Comandos Rápidos

### Desarrollo Local
```bash
./setup.sh                    # Configuración inicial
source .venv/bin/activate     # Activar entorno
uvicorn app:app --reload      # Ejecutar servidor
./test_service.sh             # Probar API
```

### Producción Docker
```bash
docker-compose up --build     # Construir y ejecutar
docker logs cutcut_cutcut_1   # Ver logs
```

### Despliegue Coolify
1. Conectar repositorio GitHub
2. Configurar variables de entorno
3. Coolify detecta Dockerfile automáticamente
4. Servicio disponible en puerto 8000

---

## 🌐 Ejemplo de Uso

```bash
curl -X POST "http://localhost:8000/split?chunk=300s&overlap=5s&format=mp3" \
  -H "X-API-Key: your-api-key" \
  -F "file=@audio.mp3" \
  | jq '.total_chunks'
```

---

## 📊 Límites por Defecto

- **Tamaño máximo**: 100 MB
- **Chunks máximos**: 50
- **Overlap mínimo**: 0s
- **Formatos**: Todos los que soporte FFmpeg

---

## 🔗 Estructura del Proyecto

```
/Users/lopezm52/Projects/CutCut/
├── app.py                 # 🎯 Aplicación principal
├── requirements.txt       # 📦 Dependencias Python
├── Dockerfile            # 🐳 Imagen Docker
├── docker-compose.yml    # 🔄 Orquestación
├── .env.example          # ⚙️  Variables de entorno
├── README.md             # 📖 Documentación principal
├── examples.md           # 💡 Ejemplos de uso
├── setup.sh              # 🚀 Script de configuración
├── test_service.sh       # 🧪 Script de pruebas
└── .github/workflows/    # 🔄 CI/CD
```

---

## ✨ Proyecto Listo para Producción

El microservicio está **completamente funcional** y listo para:
- ✅ Despliegue inmediato en Coolify
- ✅ Integración en sistemas existentes
- ✅ Escalado horizontal
- ✅ Monitoreo y observabilidad

**¡Tu microservicio CutCut está listo para rockear! 🎸**
