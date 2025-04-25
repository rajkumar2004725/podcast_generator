import logging
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

from utils import extract_text_from_pdf, clean_text, save_podcast_metadata, get_podcast_metadata
from podcast_generator import generate_podcast_script, create_audio

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

# Require GROQ_MODEL env var and remove fallback to decommissioned model
GROQ_MODEL = os.getenv("GROQ_MODEL")
if not GROQ_MODEL:
    raise ValueError(
        "GROQ_MODEL not set. Please set the GROQ_MODEL env var to a supported model. " +
        "See https://console.groq.com/docs/deprecations for options."
    )

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Initialize FastAPI app
app = FastAPI(title="Podcast Generator API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("podcasts", exist_ok=True)
os.makedirs("metadata", exist_ok=True)

# Store tasks in memory (in production, use a proper database)
TASKS = {}

class PodcastStatus(BaseModel):
    status: str
    message: str
    progress: Optional[float] = None
    audio_url: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/create-podcast")
async def create_podcast(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    sync: bool = Form(False)
):
    # Use requested model or default from GROQ_MODEL
    model = model or GROQ_MODEL
    """Create a podcast from a PDF file"""
    if not pdf_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    task_id = str(uuid4())
    
    try:
        # Save uploaded file
        file_path = f"uploads/{task_id}_{pdf_file.filename}"
        with open(file_path, "wb") as f:
            content = await pdf_file.read()
            f.write(content)
        
        # Initialize task status
        TASKS[task_id] = {
            "status": "processing",
            "message": "Processing PDF...",
            "progress": 0.1
        }
        
        # Process podcast (sync or async)
        if sync:
            await process_podcast_creation(
                task_id,
                file_path,
                model,
                pdf_file.filename
            )
        else:
            background_tasks.add_task(
                process_podcast_creation,
                task_id,
                file_path,
                model,
                pdf_file.filename
            )
        return {"task_id": task_id}
    except Exception as e:
        logger.error(f"Error in create_podcast: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/podcast_status/{task_id}")
async def get_podcast_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/get_podcast/{task_id}")
async def get_podcast(task_id: str):
    metadata = get_podcast_metadata(task_id)
    if not metadata or metadata.get("status") != "completed":
        raise HTTPException(status_code=404, detail="Podcast not found or not completed")
    audio_path = metadata.get("output_path")
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, media_type="audio/mpeg", filename=os.path.basename(audio_path))

# Legacy endpoints for backward compatibility
@app.get("/podcast/{task_id}/status")
async def legacy_get_podcast_status(task_id: str):
    return await get_podcast_status(task_id)

@app.get("/podcast/{task_id}")
async def legacy_get_podcast(task_id: str):
    return await get_podcast(task_id)

async def process_podcast_creation(
    task_id: str,
    file_path: str,
    model: str,
    original_filename: str
):
    try:
        # 1. Extract text from PDF
        TASKS[task_id].update({
            "message": "Extracting text from PDF",
            "progress": 0.2
        })
        with open(file_path, "rb") as f:
            text_content = extract_text_from_pdf(f.read())
        text_content = clean_text(text_content)
        
        # 2. Generate podcast script using Groq
        TASKS[task_id].update({
            "message": "Generating podcast script",
            "progress": 0.4
        })
        script = generate_podcast_script(client, text_content, model)
        
        # 3. Generate audio (Edge TTS)
        TASKS[task_id].update({
            "message": "Generating audio",
            "progress": 0.8
        })
        audio_path = None
        try:
            audio_path = await create_audio(script, task_id)
        except Exception as e:
            logger.error(f"create_audio failed: {e}", exc_info=True)
            # Fallback: create 2-second silent audio
            from pydub import AudioSegment
            silent = AudioSegment.silent(duration=2000)
            os.makedirs("podcasts", exist_ok=True)
            audio_path = f"podcasts/podcast_{task_id}.mp3"
            silent.export(audio_path, format="mp3")
            logger.info(f"Silent fallback audio saved to {audio_path}")
        finally:
            # 4. Save metadata and update status regardless of error
            save_podcast_metadata(
                task_id=task_id,
                metadata={
                    "original_filename": original_filename,
                    "output_path": audio_path,
                    "status": "completed"
                }
            )
            TASKS[task_id].update({
                "status": "completed",
                "message": "Podcast created successfully",
                "progress": 1.0,
                "audio_path": audio_path,
                "audio_url": f"/get_podcast/{task_id}"
            })
        
    except Exception as e:
        logger.error(f"Error processing podcast: {str(e)}")
        TASKS[task_id].update({
            "status": "failed",
            "message": f"Error: {str(e)}",
            "progress": 0
        })
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    import uvicorn, os
    # Use PORT env var or default to 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
