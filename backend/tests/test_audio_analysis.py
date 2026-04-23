"""Tests for audio analysis pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from backend.audio_analysis import (
    TrackFeatures,
    _detect_bpm,
    _detect_energy,
    _detect_intro_outro,
    _detect_key,
    _detect_phrase_boundaries,
    _check_tempo_drift,
    analyze,
    batch_analyze,
)


# ---------------------------------------------------------------------------
# Fixtures — generate synthetic audio
# ---------------------------------------------------------------------------

SR = 22050


def _make_sine(freq: float = 440.0, duration: float = 5.0, sr: int = SR) -> np.ndarray:
    """Generate a simple sine wave."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return 0.5 * np.sin(2 * np.pi * freq * t).astype(np.float32)


def _make_click_track(bpm: float = 128.0, duration: float = 10.0, sr: int = SR) -> np.ndarray:
    """Generate a click track at the given BPM for BPM detection testing."""
    n_samples = int(sr * duration)
    y = np.zeros(n_samples, dtype=np.float32)
    samples_per_beat = int(60.0 / bpm * sr)

    for i in range(0, n_samples, samples_per_beat):
        click_len = min(200, n_samples - i)
        click = 0.8 * np.sin(2 * np.pi * 1000 * np.arange(click_len) / sr)
        # Apply short envelope
        envelope = np.exp(-np.arange(click_len) / 50.0)
        y[i:i + click_len] += (click * envelope).astype(np.float32)

    return y


def _make_wav(y: np.ndarray, sr: int = SR) -> str:
    """Write audio to a temp WAV file and return the path."""
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(f.name, y, sr)
    return f.name


# ---------------------------------------------------------------------------
# TrackFeatures dataclass
# ---------------------------------------------------------------------------


def test_track_features_defaults():
    tf = TrackFeatures(file_path="/test.wav")
    assert tf.bpm == 0.0
    assert tf.key == ""
    assert tf.energy == 0.0
    assert tf.rms_envelope == []
    assert tf.phrase_boundaries == []
    assert tf.error is None


# ---------------------------------------------------------------------------
# BPM detection
# ---------------------------------------------------------------------------


def test_detect_bpm_click_track():
    y = _make_click_track(bpm=128.0, duration=15.0)
    bpm, confidence = _detect_bpm(y, SR)
    # BPM should be close to 128 (librosa may return half/double)
    assert 60 <= bpm <= 260
    assert confidence >= 0.0


def test_detect_bpm_silence():
    y = np.zeros(SR * 5, dtype=np.float32)
    bpm, confidence = _detect_bpm(y, SR)
    assert bpm >= 0
    assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# Key detection
# ---------------------------------------------------------------------------


def test_detect_key_returns_camelot():
    y = _make_sine(freq=440.0, duration=5.0)  # A4
    key, confidence = _detect_key(y, SR)
    # Should return some Camelot key
    assert len(key) >= 2
    assert key[-1] in ("A", "B")
    assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# Energy detection
# ---------------------------------------------------------------------------


def test_detect_energy_sine():
    y = _make_sine(duration=3.0)
    energy, envelope = _detect_energy(y, SR)
    assert 0.0 <= energy <= 1.0
    assert len(envelope) > 0
    assert all(0.0 <= v <= 1.0 for v in envelope)


def test_detect_energy_silence():
    y = np.zeros(SR * 3, dtype=np.float32)
    energy, envelope = _detect_energy(y, SR)
    assert energy == 0.0


# ---------------------------------------------------------------------------
# Intro/outro detection
# ---------------------------------------------------------------------------


def test_detect_intro_outro_with_silence():
    """Track with 2 seconds of silence then loud content then silence."""
    import librosa as _librosa

    silence = np.zeros(SR * 2, dtype=np.float32)
    loud = _make_sine(duration=6.0)
    y = np.concatenate([silence, loud, silence])
    rms = _librosa.feature.rms(y=y)[0]
    intro, outro = _detect_intro_outro(rms, 128.0, SR)
    assert intro >= 0
    assert outro >= 0


def test_detect_intro_outro_empty():
    intro, outro = _detect_intro_outro(np.array([]), 128.0, SR)
    assert intro == 0
    assert outro == 0


# ---------------------------------------------------------------------------
# Phrase boundaries
# ---------------------------------------------------------------------------


def test_detect_phrase_boundaries():
    y = _make_click_track(bpm=128.0, duration=30.0)
    onset_env = np.random.rand(1000).astype(np.float32)  # simplified
    boundaries = _detect_phrase_boundaries(onset_env, 128.0, SR)
    assert isinstance(boundaries, list)
    assert all(b % 8 == 0 for b in boundaries)


def test_detect_phrase_boundaries_zero_bpm():
    boundaries = _detect_phrase_boundaries(np.random.rand(100), 0.0, SR)
    assert boundaries == []


# ---------------------------------------------------------------------------
# Tempo drift
# ---------------------------------------------------------------------------


def test_check_tempo_drift_steady():
    y = _make_click_track(bpm=128.0, duration=15.0)
    has_drift, confidence = _check_tempo_drift(y, SR, 128.0)
    assert isinstance(has_drift, bool)
    assert 0.0 <= confidence <= 1.0


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------


def test_analyze_wav():
    y = _make_click_track(bpm=128.0, duration=10.0)
    path = _make_wav(y)
    features = analyze(path)

    assert features.file_path == path
    assert features.bpm > 0
    assert features.duration_s > 0
    assert features.key != ""
    assert 0.0 <= features.energy <= 1.0
    assert len(features.rms_envelope) > 0
    assert features.error is None

    # Cleanup
    Path(path).unlink(missing_ok=True)


def test_analyze_nonexistent_file():
    features = analyze("/nonexistent/track.wav")
    assert features.error is not None
    assert features.bpm == 0.0


def test_analyze_sine_wave():
    y = _make_sine(freq=440.0, duration=5.0)
    path = _make_wav(y)
    features = analyze(path)

    assert features.duration_s == pytest.approx(5.0, abs=0.1)
    assert features.error is None

    Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Batch analysis
# ---------------------------------------------------------------------------


def test_batch_analyze_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two small wav files
        for name in ("track1.wav", "track2.wav"):
            y = _make_sine(duration=2.0)
            sf.write(str(Path(tmpdir) / name), y, SR)

        results = batch_analyze(tmpdir)
        assert len(results) == 2
        assert all(r.error is None for r in results)


def test_batch_analyze_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        results = batch_analyze(tmpdir)
        assert results == []


def test_batch_analyze_nonexistent_dir():
    results = batch_analyze("/nonexistent/dir")
    assert results == []
