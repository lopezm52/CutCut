# Ejemplos de uso de CutCut API

## Ejemplos básicos

### 1. Dividir audio en chunks de 5 minutos con overlap de 10 segundos

```bash
curl -X POST "http://localhost:8000/split?chunk=5m&overlap=10s&format=mp3" \
  -H "X-API-Key: development-key-12345" \
  -F "file=@mi_audio.mp3"
```

### 2. Dividir en chunks de 30 segundos sin overlap, formato WAV

```bash
curl -X POST "http://localhost:8000/split?chunk=30s&overlap=0s&format=wav" \
  -H "X-API-Key: development-key-12345" \
  -F "file=@podcast.mp3"
```

### 3. Usando formato de tiempo HH:MM:SS

```bash
curl -X POST "http://localhost:8000/split?chunk=00:02:30&overlap=5s" \
  -H "X-API-Key: development-key-12345" \
  -F "file=@conferencia.m4a"
```

### 4. Especificando duración en milisegundos

```bash
curl -X POST "http://localhost:8000/split?chunk=120000ms&overlap=2000ms&format=flac" \
  -H "X-API-Key: development-key-12345" \
  -F "file=@musica.wav"
```

## Ejemplo de respuesta JSON

```json
{
  "filename": "ejemplo.mp3",
  "original_duration_ms": 600000,
  "chunk_duration_ms": 300000,
  "overlap_duration_ms": 5000,
  "output_format": "mp3",
  "total_chunks": 2,
  "chunks": [
    {
      "index": 0,
      "start_ms": 0,
      "end_ms": 300000,
      "duration_ms": 300000,
      "mime_type": "audio/mpeg",
      "base64": "SUQzAwAAAAAfdlBSSVYAAAAOAABQZWFr..."
    },
    {
      "index": 1,
      "start_ms": 295000,
      "end_ms": 600000,
      "duration_ms": 305000,
      "mime_type": "audio/mpeg",
      "base64": "SUQzAwAAAAAfdlBSSVYAAAAOAABQZWFr..."
    }
  ]
}
```

## Decodificar base64 a archivo

### Python

```python
import base64
import json

# Cargar respuesta JSON
with open('response.json', 'r') as f:
    data = json.load(f)

# Decodificar cada chunk
for chunk in data['chunks']:
    audio_data = base64.b64decode(chunk['base64'])
    filename = f"chunk_{chunk['index']}.{data['output_format']}"
    
    with open(filename, 'wb') as f:
        f.write(audio_data)
    
    print(f"Guardado: {filename}")
```

### JavaScript/Node.js

```javascript
const fs = require('fs');

// Cargar respuesta JSON
const data = JSON.parse(fs.readFileSync('response.json', 'utf8'));

// Decodificar cada chunk
data.chunks.forEach(chunk => {
    const audioData = Buffer.from(chunk.base64, 'base64');
    const filename = `chunk_${chunk.index}.${data.output_format}`;
    
    fs.writeFileSync(filename, audioData);
    console.log(`Guardado: ${filename}`);
});
```

## Manejo de errores

### Error 401 - API Key inválida
```json
{
  "detail": "API key inválida"
}
```

### Error 400 - Formato no soportado
```json
{
  "detail": "Formato no soportado: xyz. Formatos válidos: ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']"
}
```

### Error 413 - Archivo demasiado grande
```json
{
  "detail": "Archivo demasiado grande. Máximo permitido: 100MB"
}
```

### Error 400 - Demasiados chunks
```json
{
  "detail": "Demasiados chunks generados (75). Máximo permitido: 50"
}
```

## Formatos de entrada soportados

- MP3 (.mp3)
- WAV (.wav) 
- M4A (.m4a)
- AAC (.aac)
- FLAC (.flac)
- OGG (.ogg)
- Y cualquier formato que soporte FFmpeg

## Formatos de tiempo soportados

| Formato | Ejemplo | Descripción |
|---------|---------|-------------|
| Segundos | `300s` | 300 segundos |
| Minutos | `5m` | 5 minutos |
| HH:MM:SS | `00:05:00` | 5 minutos |
| Milisegundos | `300000ms` | 300,000 milisegundos |
| Número decimal | `300.5` | 300.5 segundos |
