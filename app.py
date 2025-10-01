import os
import re
import base64
import tempfile
from typing import Optional, List, Dict, Any
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, HTTPException, Header, Query, Depends
from fastapi.responses import JSONResponse
from pydub import AudioSegment
from pydub.utils import which
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Audio Splitting Microservice",
    description="Microservicio para dividir archivos de audio en chunks y devolverlos en base64",
    version="1.0.0"
)

# Configuración desde variables de entorno
API_KEY = os.getenv("API_KEY", "default-api-key")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "50"))

# Verificar que FFmpeg esté disponible
if not which("ffmpeg"):
    raise RuntimeError("FFmpeg no está instalado o no está en el PATH")

# Formatos de audio soportados y sus MIME types
SUPPORTED_FORMATS = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav", 
    "flac": "audio/flac",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4"
}

def parse_time_duration(duration_str: str) -> int:
    """
    Convierte una cadena de duración a milisegundos.
    
    Formatos soportados:
    - 300s (segundos)
    - 5m (minutos) 
    - 00:05:00 (HH:MM:SS)
    - 300000ms (milisegundos)
    
    Returns:
        int: Duración en milisegundos
    """
    duration_str = duration_str.strip().lower()
    
    # Formato milisegundos: 300000ms
    if duration_str.endswith('ms'):
        return int(duration_str[:-2])
    
    # Formato segundos: 300s  
    if duration_str.endswith('s'):
        return int(duration_str[:-1]) * 1000
        
    # Formato minutos: 5m
    if duration_str.endswith('m'):
        return int(duration_str[:-1]) * 60 * 1000
        
    # Formato HH:MM:SS
    if ':' in duration_str:
        parts = duration_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return (hours * 3600 + minutes * 60 + seconds) * 1000
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return (minutes * 60 + seconds) * 1000
    
    # Si no coincide con ningún formato, intentar como segundos
    try:
        return int(float(duration_str) * 1000)
    except ValueError:
        raise ValueError(f"Formato de duración no válido: {duration_str}")

def validate_api_key(x_api_key: Optional[str] = Header(None)):
    """Valida la API key del header X-API-Key"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida")
    return x_api_key

def get_mime_type(format_name: str) -> str:
    """Obtiene el MIME type para un formato de audio"""
    return SUPPORTED_FORMATS.get(format_name.lower(), "application/octet-stream")

def split_audio_to_chunks(
    audio: AudioSegment, 
    chunk_duration_ms: int, 
    overlap_ms: int = 0
) -> List[AudioSegment]:
    """
    Divide un AudioSegment en chunks con overlap opcional.
    
    Args:
        audio: AudioSegment a dividir
        chunk_duration_ms: Duración de cada chunk en milisegundos
        overlap_ms: Overlap entre chunks en milisegundos
        
    Returns:
        List[AudioSegment]: Lista de chunks de audio
    """
    chunks = []
    audio_length = len(audio)
    
    if chunk_duration_ms >= audio_length:
        # Si el chunk es mayor que el audio, devolver el audio completo
        return [audio]
    
    start = 0
    chunk_index = 0
    
    while start < audio_length and chunk_index < MAX_CHUNKS:
        end = min(start + chunk_duration_ms, audio_length)
        chunk = audio[start:end]
        chunks.append(chunk)
        
        # El siguiente chunk empieza con overlap
        start = end - overlap_ms
        
        # Si el overlap es mayor que lo que queda, terminar
        if start >= audio_length:
            break
            
        chunk_index += 1
    
    return chunks

def audio_segment_to_base64(audio: AudioSegment, format_name: str) -> str:
    """Convierte un AudioSegment a base64 en el formato especificado"""
    buffer = BytesIO()
    audio.export(buffer, format=format_name)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')

@app.get("/")
async def root():
    """Endpoint de salud del servicio"""
    return {
        "service": "Audio Splitting Microservice",
        "status": "healthy",
        "version": "1.0.0",
        "supported_formats": list(SUPPORTED_FORMATS.keys())
    }

@app.get("/health")
async def health():
    """Endpoint de health check"""
    return {"status": "healthy"}

@app.post("/split")
async def split_audio(
    file: UploadFile = File(...),
    chunk: str = Query(..., description="Duración del chunk (ej: 300s, 5m, 00:05:00, 300000ms)"),
    overlap: str = Query("5s", description="Overlap entre chunks (mismo formato que chunk)"),
    format: str = Query("mp3", description="Formato de salida (mp3, wav, flac, etc.)"),
    api_key: str = Depends(validate_api_key)
):
    """
    Divide un archivo de audio en chunks y los devuelve en base64.
    
    Args:
        file: Archivo de audio a procesar
        chunk: Duración de cada chunk
        overlap: Overlap entre chunks (opcional, default 5s)
        format: Formato de salida (opcional, default mp3)
        
    Returns:
        JSON con metadatos y chunks en base64
    """
    try:
        # Validar formato de salida
        if format.lower() not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato no soportado: {format}. Formatos válidos: {list(SUPPORTED_FORMATS.keys())}"
            )
        
        # Validar tamaño del archivo
        file_size_mb = len(await file.read()) / (1024 * 1024)
        await file.seek(0)  # Resetear posición del archivo
        
        if file_size_mb > MAX_UPLOAD_MB:
            raise HTTPException(
                status_code=413, 
                detail=f"Archivo demasiado grande. Máximo permitido: {MAX_UPLOAD_MB}MB"
            )
        
        # Parsear duración del chunk y overlap
        try:
            chunk_duration_ms = parse_time_duration(chunk)
            overlap_duration_ms = parse_time_duration(overlap)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Validar que overlap no sea mayor que chunk
        if overlap_duration_ms >= chunk_duration_ms:
            raise HTTPException(
                status_code=400, 
                detail="El overlap no puede ser mayor o igual que la duración del chunk"
            )
        
        # Crear archivo temporal para procesar
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Cargar audio con pydub
            audio = AudioSegment.from_file(temp_file_path)
            original_duration_ms = len(audio)
            
            # Dividir en chunks
            chunks = split_audio_to_chunks(audio, chunk_duration_ms, overlap_duration_ms)
            
            if len(chunks) > MAX_CHUNKS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Demasiados chunks generados ({len(chunks)}). Máximo permitido: {MAX_CHUNKS}"
                )
            
            # Convertir chunks a base64
            chunk_data = []
            for i, chunk in enumerate(chunks):
                start_ms = i * (chunk_duration_ms - overlap_duration_ms)
                if i == 0:
                    start_ms = 0
                
                end_ms = min(start_ms + len(chunk), original_duration_ms)
                
                chunk_b64 = audio_segment_to_base64(chunk, format.lower())
                
                chunk_info = {
                    "index": i,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "duration_ms": len(chunk),
                    "mime_type": get_mime_type(format),
                    "base64": chunk_b64
                }
                chunk_data.append(chunk_info)
            
            # Preparar respuesta
            response = {
                "filename": file.filename,
                "original_duration_ms": original_duration_ms,
                "chunk_duration_ms": chunk_duration_ms,
                "overlap_duration_ms": overlap_duration_ms,
                "output_format": format.lower(),
                "total_chunks": len(chunks),
                "chunks": chunk_data
            }
            
            return JSONResponse(content=response)
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando audio: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
