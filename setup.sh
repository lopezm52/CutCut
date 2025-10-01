#!/bin/bash

# Script de inicialización rápida para CutCut
# Este script configura todo lo necesario para ejecutar el proyecto

echo "🎵 Configurando CutCut Audio Splitting Microservice..."

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado"
    exit 1
fi

# Verificar si FFmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg no está instalado. Instalando..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "❌ Homebrew no está instalado. Instala FFmpeg manualmente:"
            echo "   brew install ffmpeg"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update && sudo apt-get install -y ffmpeg
    else
        echo "❌ OS no soportado para instalación automática de FFmpeg"
        exit 1
    fi
fi

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv .venv
fi

# Activar entorno virtual e instalar dependencias
echo "📥 Instalando dependencias..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    echo "⚙️  Creando archivo .env..."
    cp .env.example .env
    echo "🔑 Edita el archivo .env para configurar tu API_KEY"
fi

echo ""
echo "✅ Configuración completada!"
echo ""
echo "🚀 Para ejecutar el servicio:"
echo "   source .venv/bin/activate"
echo "   uvicorn app:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "🐳 Para ejecutar con Docker:"
echo "   docker-compose up --build"
echo ""
echo "🧪 Para probar el servicio:"
echo "   ./test_service.sh"
echo ""
echo "📚 Consulta README.md y examples.md para más información"
