"""Audio pipeline test script.

Tests the audio capture → resample → VAD pipeline.
Run: python test_audio.py
"""

import time
import numpy as np
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from audio_capture import AudioCapture
from resample import resample_to_16khz
from vad_processor import SileroVADProcessor


def main():
    """Run audio pipeline test: capture → resample → VAD."""
    print("=" * 60)
    print("SimulTransOverlay — Audio Pipeline Test")
    print("=" * 60)
    print()
    print("This test captures system audio and runs it through the pipeline.")
    print("Press Ctrl+C to stop.")
    print()

    # Initialize VAD
    vad = SileroVADProcessor()
    print(f"[VAD] Sample rate: {vad.sample_rate}Hz")
    print(f"[VAD] Silence threshold: {vad.silence_threshold}s")
    print()

    segment_count = 0
    chunk_count = 0

    def audio_handler(audio_data: np.ndarray):
        """Handle incoming audio from WASAPI capture."""
        nonlocal segment_count, chunk_count

        # Resample: 48kHz stereo → 16kHz mono
        mono_16khz = resample_to_16khz(audio_data)
        chunk_count += 1

        # Process in 32ms chunks (512 samples @ 16kHz)
        chunk_size = 512
        for start in range(0, len(mono_16khz), chunk_size):
            chunk = mono_16khz[start:start + chunk_size]
            if len(chunk) < chunk_size // 2:
                continue  # skip tiny trailing chunks
            if len(chunk) != chunk_size:
                # Pad short chunk
                padded = np.zeros(chunk_size, dtype=np.float32)
                padded[:len(chunk)] = chunk
                chunk = padded

            prob = vad.process_chunk(chunk)

            if vad.should_segment():
                segment = vad.pop_segment()
                duration = len(segment) / 16000
                segment_count += 1
                print(f"\n--- Segment #{segment_count} ({duration:.2f}s) ---")

    # Start capture
    capture = AudioCapture()
    capture.set_callback(audio_handler)
    capture.start()
    print("[Capture] WASAPI Loopback started")
    print("[Info] Play some audio (YouTube, music, etc.)")
    print()

    try:
        while True:
            time.sleep(1)
            if chunk_count > 0 and chunk_count % 60 == 0:
                print(f"[Heartbeat] Chunks: {chunk_count}, Segments: {segment_count}")
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        capture.stop()
        print(f"[Done] Processed {chunk_count} chunks, detected {segment_count} segments")


if __name__ == "__main__":
    main()
