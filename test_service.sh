#!/bin/bash

# Script de prueba para el microservicio CutCut
# Asegúrate de tener un archivo de audio de prueba llamado 'test.mp3'

API_KEY="your-secret-api-key-here"
BASE_URL="http://localhost:8000"
AUDIO_FILE="test.mp3"

echo "🎵 Probando microservicio CutCut..."
echo ""

# Test 1: Health check
echo "1. Health check..."
curl -s "$BASE_URL/health" | jq '.'
echo ""

# Test 2: Información del servicio
echo "2. Información del servicio..."
curl -s "$BASE_URL/" | jq '.'
echo ""

# Test 3: Split con parámetros básicos (necesita archivo de audio)
if [ -f "$AUDIO_FILE" ]; then
    echo "3. Dividiendo audio en chunks de 30 segundos..."
    curl -X POST "$BASE_URL/split?chunk=30s&overlap=2s&format=mp3" \
         -H "X-API-Key: $API_KEY" \
         -F "file=@$AUDIO_FILE" \
         -s | jq '.filename, .total_chunks, .original_duration_ms'
    echo ""
else
    echo "3. ⚠️  No se encontró archivo '$AUDIO_FILE' para probar"
    echo "   Crea un archivo de audio llamado '$AUDIO_FILE' para probar completamente"
    echo ""
fi

# Test 4: Error sin API key
echo "4. Probando error sin API key..."
curl -X POST "$BASE_URL/split?chunk=30s" \
     -F "file=@README.md" \
     -s | jq '.'
echo ""

echo "✅ Pruebas completadas"
