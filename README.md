# PDF to Podcast Generator with Groq AI

This project converts PDF documents into engaging podcasts using Groq's AI models for content generation and gTTS for text-to-speech conversion.

## Features

- PDF text extraction
- AI-powered content summarization
- Conversational podcast script generation
- Text-to-speech with different voices for host and guest
- Background task processing
- Progress tracking
- Optional background music support

## Setup

1. **Clone the repository and create virtual environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Unix/macOS
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Add your Groq API key (get it from https://console.groq.com/keys)
   ```bash
   cp .env.example .env
   ```

4. **Run the application**:
   ```bash
   uvicorn app:app --reload
   ```

## API Endpoints

- `GET /health`: Health check endpoint
- `POST /create-podcast`: Create a new podcast from PDF
  - Required: PDF file
  - Optional: AI model name (default: mixtral-8x7b-32768)
- `GET /podcast-status/{task_id}`: Check podcast creation status
- `GET /podcast/{task_id}`: Download generated podcast

## Usage Example

1. **Check server health**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Create a podcast**:
   ```bash
   curl -X POST http://localhost:8000/create-podcast \
     -F "pdf_file=@your_document.pdf" \
     -F "model=mixtral-8x7b-32768"
   ```

3. **Check status**:
   ```bash
   curl http://localhost:8000/podcast-status/{task_id}
   ```

4. **Download podcast**:
   ```bash
   curl http://localhost:8000/podcast/{task_id} --output podcast.mp3
   ```

## Project Structure

```
podcast_groq/
├── app.py              # FastAPI application
├── utils.py            # Utility functions
├── podcast_generator.py # Podcast generation logic
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
└── README.md          # This file
```

## Dependencies

- FastAPI
- Groq AI
- PyPDF2
- gTTS (Google Text-to-Speech)
- pydub
- python-multipart
- python-dotenv

## Note

Make sure you have enough Groq API credits for text generation. The application uses Groq's Mixtral model by default, which provides high-quality results for content generation.
