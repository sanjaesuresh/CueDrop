"""Essentia audio analysis microservice.

Runs inside Docker (x86 via Rosetta) since essentia has no ARM Mac wheels.
The main backend calls this over HTTP to get audio features.
"""

from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
import tempfile
import os

app = FastAPI(title="CueDrop Essentia Service", version="0.1.0")


@app.get("/health")
async def health():
    import essentia
    return {"status": "ok", "essentia_version": essentia.__version__}


@app.post("/analyze")
async def analyze(file: UploadFile):
    """Analyze an audio file and return key, BPM, energy, and other features."""
    import essentia.standard as es
    import numpy as np

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        audio = es.MonoLoader(filename=tmp_path, sampleRate=44100)()

        # Key detection
        key_extractor = es.KeyExtractor()
        key, scale, key_strength = key_extractor(audio)

        # BPM detection
        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio)

        # Energy (RMS)
        energy = float(es.Energy()(audio))
        rms = float(np.sqrt(energy / len(audio)))

        # Loudness
        loudness = float(es.Loudness()(audio))

        # Danceability
        danceability, _ = es.Danceability()(audio)

        return JSONResponse({
            "key": key,
            "scale": scale,
            "key_strength": round(float(key_strength), 3),
            "bpm": round(float(bpm), 1),
            "beats_count": len(beats),
            "energy": round(rms, 4),
            "loudness": round(float(loudness), 4),
            "danceability": round(float(danceability), 4),
            "duration_sec": round(len(audio) / 44100, 2),
        })
    finally:
        os.unlink(tmp_path)
