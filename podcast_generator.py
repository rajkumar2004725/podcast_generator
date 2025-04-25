from typing import Dict
from pydub import AudioSegment
import os
import unicodedata
import re
import time
import traceback
import asyncio
import edge_tts
import shutil
import gtts

# Configure FFmpeg path for pydub
ffmpeg_default = shutil.which("ffmpeg")
ffmpeg_local = os.path.join(os.getcwd(), "ffmpeg_temp", "ffmpeg-master-latest-win64-gpl", "bin", "ffmpeg.exe")
if os.path.exists(ffmpeg_local):
    AudioSegment.converter = ffmpeg_local
elif ffmpeg_default:
    AudioSegment.converter = ffmpeg_default
else:
    print("WARNING: FFmpeg not found. Install it or place binaries in ffmpeg_temp.")

# Add ffmpeg_local directory to PATH for edge-tts
ffmpeg_local_dir = os.path.dirname(ffmpeg_local)
if os.path.isdir(ffmpeg_local_dir):
    os.environ["PATH"] = ffmpeg_local_dir + os.pathsep + os.environ.get("PATH", "")

def sanitize_tts_text(text: str) -> str:
    # Replace smart quotes and dashes
    replacements = {
        '“': '"', '”': '"', '‘': "'", '’': "'", '—': '-', '–': '-',
        '…': '...',
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    # Normalize unicode and encode to ASCII, ignoring errors
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text.strip()


def split_text_for_tts(text, max_length=200):
    """
    Split text into <=max_length char chunks, breaking at sentence boundaries if possible.
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    if len(text) <= max_length:
        return [text]
    # Split at sentence boundaries
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current = ''
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_length:
            current = (current + ' ' + sent).strip()
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    # If any chunk is still too long, split hard
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_length:
            final_chunks.append(chunk)
        else:
            for i in range(0, len(chunk), max_length):
                final_chunks.append(chunk[i:i+max_length])
    return [c for c in final_chunks if c.strip()]


def generate_podcast_script(client, content: str, model: str) -> str:
    """Generate a podcast script using Groq API."""
    try:
        print(f"Generating script with content length: {len(content)}")
        print("Content preview:", content[:200])
        
        # First, generate a summary
        summary_prompt = f"""Summarize the following content into 3-4 key points that would be interesting for a podcast. DO NOT include any meta-commentary, explanations, or thinking out loud. Just provide the summary directly. NEVER output <think> or any commentary:

{content[:4000]}"""

        print("Generating summary...")
        summary_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a direct and concise podcast content summarizer. You never think out loud or include meta-commentary in your responses. NEVER output <think>."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        summary = summary_response.choices[0].message.content.strip()
        print("Summary generated:", summary[:200])

        # Then, create a conversational script
        script_prompt = f"""Create a podcast script discussing these points:
        
{summary}
        
SCRIPT FORMAT EXAMPLES (copy this style):
Host: Welcome to the show! Today we're discussing...
Guest: Thanks for having me! I'm excited to...
Host: Let's dive into our first topic...
Guest: Well, that's a great question...
        
REQUIREMENTS:
1. Every line MUST start with exactly "Host:" or "Guest:" (case-insensitive, no spaces before colon)
2. Write only natural, conversational dialogue
3. 6-8 exchanges total
4. End with a clear conclusion
5. DO NOT include any meta-commentary, explanations, <think>, or instructions
6. DO NOT include any placeholders or [brackets]
7. Output ONLY the script lines, nothing else
        
OUTPUT THE SCRIPT DIRECTLY, NO COMMENTARY OR HEADERS:"""
        
        print("Generating conversation script...")
        script_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a podcast script writer that ONLY outputs scripts in Host/Guest format. You never include any meta-commentary, explanations, or thinking out loud. NEVER output <think>. Output ONLY the script lines."},
                {"role": "user", "content": script_prompt}
            ],
            temperature=0.7,  # Add some creativity but not too much
            max_tokens=2000,  # Limit length to avoid cut-off
        )
        
        raw_script = script_response.choices[0].message.content.strip()
        print("Raw script from Groq:", raw_script[:300])
        
        # Clean up the script
        lines = []
        for line in raw_script.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Accept "Host:", "Host :", "host:", "guest:" etc.
            if line.lower().startswith("host:") or line.lower().startswith("host :"):
                text = line.split(":", 1)[1].strip()
                if text:
                    lines.append(f"Host: {text}")
            elif line.lower().startswith("guest:") or line.lower().startswith("guest :"):
                text = line.split(":", 1)[1].strip()
                if text:
                    lines.append(f"Guest: {text}")
        
        script = '\n'.join(lines)
        print("Cleaned script, length:", len(script))
        print("Cleaned script preview:", script[:300])
        
        # If script is empty, log the raw script for debugging
        if not script.strip():
            print("WARNING: Cleaned script is empty! Raw script was:")
            print(raw_script)
            raise Exception("Script generated by Groq API was empty or invalid. See logs for raw output.")
        
        return script
    
    except Exception as e:
        print(f"Error in generate_podcast_script: {str(e)}")
        raise

async def synthesize_edge_tts(text, voice, outfile):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(outfile)

async def create_audio(script: str, task_id: str) -> str:
    """Create audio file from the podcast script using edge-tts."""
    try:
        print(f"Creating audio for script length: {len(script)}")
        print("Script preview:", script[:200])
        
        # Split script into segments
        segments = []
        current_speaker = None
        current_text = []
        
        # Clean up the script first
        script = script.strip()
        if not script:
            raise Exception("Empty script received")
            
        for line in script.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.lower().startswith(('host:', 'guest:')):
                # If we have a previous segment, save it
                if current_speaker and current_text:
                    text = ' '.join(current_text).strip()
                    if text:
                        segments.append((current_speaker, text))
                    else:
                        print(f"Skipped empty segment for {current_speaker}")
                    current_text = []
                
                # Start new segment
                parts = line.split(':', 1)
                if len(parts) == 2:
                    current_speaker = parts[0].lower()
                    text = parts[1].strip()
                    if text:
                        current_text = [text]
                    else:
                        current_text = []
            else:
                # Continue with current segment if we have one
                if current_text is not None and line:
                    current_text.append(line)
        
        # Add the last segment
        if current_speaker and current_text:
            text = ' '.join(current_text).strip()
            if text:
                segments.append((current_speaker, text))
            else:
                print(f"Skipped empty segment for {current_speaker}")
        
        # Print all segments for debugging
        print("All segments before audio generation:")
        for idx, (speaker, text) in enumerate(segments):
            print(f"Segment {idx+1}: Speaker={speaker}, Length={len(text)}, Text='{text[:50]}'")
        
        # If all segments are empty, raise an error
        if not segments or all(not text.strip() for _, text in segments):
            raise Exception(f"All segments are empty! Segments: {segments}")
        
        print(f"Found {len(segments)} segments")
        for i, (speaker, text) in enumerate(segments):
            print(f"Segment {i + 1}: {speaker} - {text[:50]}...")
        
        # Create output directory if it doesn't exist
        os.makedirs("podcasts", exist_ok=True)
        
        # Create temporary directory for segment files
        temp_dir = os.path.join("podcasts", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate audio segments with different voices using edge-tts
        audio_segments = []
        seg_number = 0
        for i, (speaker, text) in enumerate(segments):
            if not text.strip():
                print(f"Skipping empty segment {i+1} for {speaker}")
                continue
            sanitized_chunks = [sanitize_tts_text(chunk) for chunk in split_text_for_tts(text)]
            for chunk_idx, chunk in enumerate(sanitized_chunks):
                if not chunk:
                    print(f"Skipping chunk {chunk_idx+1} of segment {i+1} after sanitization (empty text)")
                    continue
                seg_number += 1
                print(f"[AUDIO GEN] Segment {i+1} Chunk {chunk_idx+1} Speaker={speaker}, Length={len(chunk)}, Text='{chunk[:50]}'")
                print(f"[DEBUG] chunk repr: {repr(chunk)}")
                print(f"[DEBUG] chunk type: {type(chunk)}")
                print(f"[DEBUG] chunk length: {len(chunk)}")
                temp_path = os.path.join(temp_dir, f"segment_{i}_{chunk_idx}.mp3")
                # Use primary and fallback voices for host/guest
                primary_voice = "en-US-GuyNeural" if speaker == "host" else "en-GB-LibbyNeural"
                fallback_map = {"en-US-GuyNeural": "en-US-AriaNeural", "en-GB-LibbyNeural": "en-GB-RyanNeural"}
                voices = [primary_voice, fallback_map.get(primary_voice)]
                success = False
                # Try primary and fallback voices; skip chunk if both fail
                for v in voices:
                    try:
                        await synthesize_edge_tts(chunk, v, temp_path)
                        await asyncio.sleep(0.5)
                        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                            success = True
                            break
                        print(f"Empty audio with voice {v}")
                    except Exception as e2:
                        print(f"Error generating with voice {v}: {e2}")
                        # Continue to next voice
                        continue
                # Fallback to gTTS if Edge TTS fails
                if not success:
                    print(f"Edge TTS failed for segment {i+1} chunk {chunk_idx+1}, trying gTTS fallback")
                    try:
                        tts = gtts.gTTS(text=chunk, lang='en')
                        tts.save(temp_path)
                        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                            success = True
                            print(f"gTTS fallback succeeded for chunk {chunk_idx+1}")
                        else:
                            print(f"gTTS fallback generated empty file for chunk {chunk_idx+1}")
                    except Exception as e_tts:
                        print(f"gTTS fallback failed for chunk {chunk_idx+1}: {e_tts}")
                if not success:
                    print(f"Skipping segment {i+1} chunk {chunk_idx+1}: no audio generated after fallback")
                    continue
                # Add pause between segments
                if seg_number > 1:
                    pause_path = os.path.join(temp_dir, f"pause_{i}_{chunk_idx}.mp3")
                    try:
                        await synthesize_edge_tts("...", primary_voice, pause_path)
                        await asyncio.sleep(0.2)
                        if os.path.exists(pause_path) and os.path.getsize(pause_path) > 0:
                            with open(pause_path, 'rb') as f:
                                audio_segments.append(f.read())
                        else:
                            print(f"Skipping pause audio: file empty or missing")
                    except Exception as e_pause:
                        print(f"Error generating pause audio: {e_pause}")
                    finally:
                        if os.path.exists(pause_path):
                            os.remove(pause_path)
                # Add segment audio
                with open(temp_path, 'rb') as f:
                    audio_segments.append(f.read())
                os.remove(temp_path)
        
        if not audio_segments:
            print("No audio segments were generated; creating silent fallback audio")
            # Create a 1-second silent audio segment as fallback
            from pydub import AudioSegment as _AudioSegment
            silent = _AudioSegment.silent(duration=1000)
            output_path = f"podcasts/podcast_{task_id}.mp3"
            silent.export(output_path, format="mp3")
            print(f"Silent audio saved to {output_path}")
            return output_path
        
        # Combine all segments into final audio file
        output_path = f"podcasts/podcast_{task_id}.mp3"
        print(f"Generating final audio file at: {output_path}")
        
        with open(output_path, 'wb') as f:
            for segment in audio_segments:
                f.write(segment)
        
        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except:
            pass
        
        print("Audio file created successfully")
        return output_path
    
    except Exception as e:
        print(f"Error in create_audio: {e}")
        # Fallback to silent audio on any error
        print("Creating 1-second silent fallback audio due to error.")
        from pydub import AudioSegment as _AudioSegment
        silent = _AudioSegment.silent(duration=1000)
        output_path = f"podcasts/podcast_{task_id}.mp3"
        silent.export(output_path, format="mp3")
        print(f"Silent fallback audio saved to {output_path}")
        return output_path

def add_background_music(audio_path: str, music_path: str, output_path: str):
    """Add background music to the podcast."""
    try:
        # Load the podcast audio and background music
        podcast = AudioSegment.from_mp3(audio_path)
        music = AudioSegment.from_mp3(music_path)
        
        # Loop music if it's shorter than the podcast
        while len(music) < len(podcast):
            music = music + music
        
        # Trim music to podcast length
        music = music[:len(podcast)]
        
        # Lower the volume of the background music
        music = music - 20  # Reduce volume by 20dB
        
        # Mix podcast and music
        final_audio = podcast.overlay(music)
        
        # Export the final mix
        final_audio.export(output_path, format="mp3")
        
        return output_path
    
    except Exception as e:
        print(f"Error adding background music: {str(e)}")
        raise Exception(f"Error adding background music: {str(e)}")
