# Coolify Configuration
# Este archivo contiene información específica para el despliegue en Coolify

# Variables de entorno requeridas en Coolify:
# API_KEY=tu-api-key-secreta
# MAX_UPLOAD_MB=100
# MAX_CHUNKS=50

# Puerto de la aplicación
EXPOSE_PORT=8000

# Health check endpoint
HEALTH_CHECK_PATH=/health

# Build context
DOCKERFILE_PATH=./Dockerfile

# Recursos recomendados:
# CPU: 1 core
# RAM: 512MB - 1GB
# Storage: 2GB

# Comandos útiles para debug:
# docker logs <container-name>
# docker exec -it <container-name> /bin/bash
