import os
import re
import base64
import tempfile
import secrets
from typing import Optional, List, Dict, Any
from io import BytesIO

from fastapi import FastAPI, File, UploadFile, HTTPException, Header, Query, Depends
from fastapi.concurrency import run_in_threadpool
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

async def validate_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Validates the API Key provided in the header.
    """
    if not API_KEY:
        # If no API key is configured, allow all requests (development mode)
        # Ideally, log a warning here.
        return x_api_key

    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return x_api_key

def get_ffmpeg_format(format_name: str) -> str:
    """Mapea el formato solicitado al formato FFmpeg correcto"""
    format_map = {
        'mp3': 'mp3',
        'wav': 'wav',
        'flac': 'flac',
        'ogg': 'ogg',
        'm4a': 'mp4',  # M4A usa contenedor MP4 en FFmpeg
        'aac': 'adts'  # AAC usa contenedor ADTS
    }
    return format_map.get(format_name.lower(), 'mp3')

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
    step = chunk_duration_ms - overlap_ms  # Paso real entre chunks
    
    while start < audio_length and chunk_index < MAX_CHUNKS:
        end = min(start + chunk_duration_ms, audio_length)
        
        # Solo agregar chunk si tiene contenido mínimo (>1 segundo)
        if end - start > 1000:
            chunk = audio[start:end]
            chunks.append(chunk)
            chunk_index += 1
        else:
            # Si el chunk restante es muy pequeño, terminar
            break
        
        # Avanzar al siguiente chunk
        start += step
    
    return chunks

def audio_segment_to_base64(audio: AudioSegment, format_name: str) -> str:
    """Convierte un AudioSegment a base64 en el formato especificado"""
    buffer = BytesIO()
    ffmpeg_format = get_ffmpeg_format(format_name)
    audio.export(buffer, format=ffmpeg_format)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')

def process_audio_sync(
    file_content: bytes,
    chunk_ms: int,
    overlap_ms: int,
    format_name: str,
    original_filename: str
) -> Dict[str, Any]:
    """
    Synchronous function to process audio splitting.
    This should be run in a threadpool to avoid blocking the event loop.
    """
    # Create a temporary file to handle format detection better or use BytesIO
    # Pydub handles BytesIO well for most formats
    file_obj = BytesIO(file_content)
    
    try:
        # Load audio
        audio = AudioSegment.from_file(file_obj)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error decoding audio file: {str(e)}")

    # Split audio
    chunks = split_audio_to_chunks(audio, chunk_ms, overlap_ms)
    
    # Convert chunks to base64
    result_chunks = []
    mime_type = get_mime_type(format_name)
    
    for i, chunk_audio in enumerate(chunks):
        base64_data = audio_segment_to_base64(chunk_audio, format_name)
        
        # Calculate timestamps
        start_ms = i * (chunk_ms - overlap_ms)
        end_ms = start_ms + len(chunk_audio)
        
        result_chunks.append({
            "index": i,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": len(chunk_audio),
            "format": format_name,
            "mime_type": mime_type,
            "data": base64_data
        })
        
    return {
        "filename": original_filename,
        "original_duration_ms": len(audio),
        "chunk_duration_ms": chunk_ms,
        "overlap_ms": overlap_ms,
        "total_chunks": len(chunks),
        "format": format_name,
        "chunks": result_chunks
    }

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
        JSON con los chunks en base64 y metadatos
    """
    # Validar formato de salida
    format_name = format.lower()
    if format_name not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato no soportado. Formatos válidos: {', '.join(SUPPORTED_FORMATS.keys())}"
        )
    
    # Parsear duraciones
    try:
        chunk_ms = parse_time_duration(chunk)
        overlap_ms = parse_time_duration(overlap)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Validaciones lógicas
    if chunk_ms < 1000:
        raise HTTPException(status_code=400, detail="El tamaño del chunk debe ser al menos 1 segundo")
        
    if overlap_ms >= chunk_ms:
        raise HTTPException(status_code=400, detail="El overlap debe ser menor que el tamaño del chunk")

    # Validar tamaño del archivo (aproximado)
    # Nota: file.size no siempre está disponible o es preciso hasta leerlo, 
    # pero podemos verificar el Content-Length header si existe.
    # Aquí leemos el archivo en memoria, lo cual consume RAM.
    # Para archivos muy grandes, esto podría ser un problema, pero dado el requerimiento actual:
    
    try:
        content = await file.read()
        
        if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
             raise HTTPException(
                status_code=413, 
                detail=f"El archivo excede el límite de {MAX_UPLOAD_MB}MB"
            )
            
        # Procesar en threadpool para no bloquear el event loop
        result = await run_in_threadpool(
            process_audio_sync,
            content,
            chunk_ms,
            overlap_ms,
            format_name,
            file.filename or "audio"
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno procesando el audio: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
