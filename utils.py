import io
import json
import os
import PyPDF2
from typing import Dict, Optional

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        print(f"Extracting text from PDF, size: {len(pdf_bytes)} bytes")
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        print(f"PDF has {len(pdf_reader.pages)} pages")
        
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            print(f"Page {i+1} extracted, length: {len(page_text)}")
            text += page_text + "\n"
        
        print(f"Total extracted text length: {len(text)}")
        print("Text preview:", text[:200])
        return text
    except Exception as e:
        print(f"Error in extract_text_from_pdf: {str(e)}")
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def clean_text(text: str) -> str:
    """Clean and normalize text."""
    print(f"Cleaning text of length: {len(text)}")
    # Remove extra whitespace
    text = " ".join(text.split())
    # Remove special characters that might affect speech
    text = text.replace("•", "")
    text = text.replace("…", "...")
    print(f"Cleaned text length: {len(text)}")
    print("Cleaned text preview:", text[:200])
    return text

def save_podcast_metadata(task_id: str, metadata: Dict) -> None:
    """Save podcast metadata to a JSON file."""
    try:
        os.makedirs("metadata", exist_ok=True)
        metadata_path = os.path.join("metadata", f"{task_id}.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
    except Exception as e:
        raise Exception(f"Error saving metadata: {str(e)}")

def get_podcast_metadata(task_id: str) -> Optional[Dict]:
    """Get podcast metadata from JSON file."""
    try:
        metadata_path = os.path.join("metadata", f"{task_id}.json")
        if not os.path.exists(metadata_path):
            return None
        with open(metadata_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Error reading metadata: {str(e)}")
