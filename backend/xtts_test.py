# backend/test_tts.py
from TTS.api import TTS
import os
from pathlib import Path

def test_tts():
    print("Starting TTS test...")
    
    # Check for Jarvis.wav
    speaker_path = Path("Jarvis.wav")
    print(f"Speaker file exists: {speaker_path.exists()}")
    print(f"Speaker file absolute path: {speaker_path.absolute()}")
    
    # Create output directory
    output_dir = Path("audio_cache")
    output_dir.mkdir(exist_ok=True)
    print(f"Created output directory at: {output_dir.absolute()}")
    
    # Initialize TTS
    print("Initializing TTS...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)
    print("TTS initialized successfully")
    
    # Generate test audio
    test_text = "This is a test of the text to speech system."
    output_path = output_dir / "test.wav"
    print(f"Generating test audio to: {output_path}")
    
    tts.tts_to_file(
        text=test_text,
        file_path=str(output_path),
        speaker_wav="Jarvis.wav",
        language="en"
    )
    
    print(f"Audio file generated: {output_path.exists()}")
    if output_path.exists():
        print(f"Audio file size: {output_path.stat().st_size} bytes")

if __name__ == "__main__":
    test_tts()