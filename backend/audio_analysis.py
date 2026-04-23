"""Audio analysis pipeline — BPM, key, energy, mix point detection (Phase 2 Stream B)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import librosa
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Key detection helpers
# ---------------------------------------------------------------------------

# Chroma-to-key mapping (Krumhansl-Schmuckler profiles)
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Camelot wheel mapping for detected keys
_KEY_TO_CAMELOT: dict[str, str] = {
    "C major": "8B", "G major": "9B", "D major": "10B", "A major": "11B",
    "E major": "12B", "B major": "1B", "F# major": "2B", "C# major": "3B",
    "G# major": "4B", "D# major": "5B", "A# major": "6B", "F major": "7B",
    "A minor": "8A", "E minor": "9A", "B minor": "10A", "F# minor": "11A",
    "C# minor": "12A", "G# minor": "1A", "D# minor": "2A", "A# minor": "3A",
    "F minor": "4A", "C minor": "5A", "G minor": "6A", "D minor": "7A",
}


def _detect_key(y: np.ndarray, sr: int) -> tuple[str, float]:
    """Detect musical key using chroma features and Krumhansl-Schmuckler.

    Returns (camelot_key, confidence) where confidence is 0.0–1.0.
    """
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)

    # Correlate with major and minor profiles for all 12 rotations
    best_corr = -1.0
    best_key = "8B"
    second_best = -1.0

    for i in range(12):
        major_corr = float(np.corrcoef(np.roll(chroma_mean, -i), _MAJOR_PROFILE)[0, 1])
        minor_corr = float(np.corrcoef(np.roll(chroma_mean, -i), _MINOR_PROFILE)[0, 1])

        for corr, mode in [(major_corr, "major"), (minor_corr, "minor")]:
            if corr > best_corr:
                second_best = best_corr
                best_corr = corr
                key_name = f"{_NOTE_NAMES[i]} {mode}"
                best_key = _KEY_TO_CAMELOT.get(key_name, "8B")
            elif corr > second_best:
                second_best = corr

    # Confidence based on margin between best and second-best correlation
    confidence = max(0.0, min(1.0, (best_corr - second_best) * 5.0))
    return best_key, confidence


# ---------------------------------------------------------------------------
# TrackFeatures
# ---------------------------------------------------------------------------


@dataclass
class TrackFeatures:
    """Extracted audio features for a track."""

    file_path: str
    bpm: float = 0.0
    bpm_confidence: float = 0.0
    key: str = ""  # Camelot notation (e.g., "8A", "11B")
    key_confidence: float = 0.0
    energy: float = 0.0  # 0.0–1.0
    rms_envelope: list[float] = field(default_factory=list)
    intro_bars: int = 0
    outro_bars: int = 0
    phrase_boundaries: list[int] = field(default_factory=list)  # bar numbers
    duration_s: float = 0.0
    has_tempo_drift: bool = False
    beat_grid_confidence: float = 1.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _detect_bpm(y: np.ndarray, sr: int) -> tuple[float, float]:
    """Detect BPM and confidence.

    Returns (bpm, confidence) where confidence is 0.0–1.0.
    """
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)

    # tempo may be an array; extract scalar
    bpm = float(np.atleast_1d(tempo)[0])

    # Confidence: check consistency of inter-beat intervals
    if len(beats) < 4:
        return bpm, 0.3

    beat_times = librosa.frames_to_time(beats, sr=sr)
    ibis = np.diff(beat_times)
    if len(ibis) == 0:
        return bpm, 0.3

    median_ibi = float(np.median(ibis))
    if median_ibi == 0:
        return bpm, 0.3

    deviations = np.abs(ibis - median_ibi) / median_ibi
    mean_dev = float(np.mean(deviations))
    confidence = max(0.0, min(1.0, 1.0 - mean_dev * 5.0))

    return bpm, confidence


def _detect_energy(y: np.ndarray, sr: int) -> tuple[float, list[float]]:
    """Compute overall energy and RMS envelope.

    Returns (energy_0_to_1, rms_envelope_downsampled).
    """
    rms = librosa.feature.rms(y=y)[0]
    # Normalize to 0–1
    rms_max = float(np.max(rms)) if len(rms) > 0 else 1.0
    if rms_max == 0:
        rms_max = 1.0

    energy = float(np.mean(rms) / rms_max)

    # Downsample envelope to ~1 value per second
    hop_length = 512
    frames_per_second = sr / hop_length
    step = max(1, int(frames_per_second))
    envelope = (rms[::step] / rms_max).tolist()

    return energy, envelope


def _detect_intro_outro(rms: np.ndarray, bpm: float, sr: int, hop: int = 512) -> tuple[int, int]:
    """Detect intro and outro length in bars.

    Uses energy threshold to find where main content begins/ends.
    """
    if len(rms) < 10 or bpm <= 0:
        return 0, 0

    rms_max = float(np.max(rms))
    if rms_max == 0:
        return 0, 0

    threshold = 0.15 * rms_max
    frames_per_bar = (sr / hop) * (4 * 60.0 / bpm)
    if frames_per_bar <= 0:
        return 0, 0

    # Intro: first frame above threshold
    intro_frame = 0
    for i, val in enumerate(rms):
        if val > threshold:
            intro_frame = i
            break
    intro_bars = max(0, int(intro_frame / frames_per_bar))

    # Outro: last frame above threshold
    outro_frame = len(rms)
    for i in range(len(rms) - 1, -1, -1):
        if rms[i] > threshold:
            outro_frame = len(rms) - i
            break
    outro_bars = max(0, int(outro_frame / frames_per_bar))

    return intro_bars, outro_bars


def _detect_phrase_boundaries(onset_env: np.ndarray, bpm: float, sr: int, hop: int = 512) -> list[int]:
    """Detect phrase boundaries (bar numbers where 8/16-bar phrases start).

    Uses spectral flux peaks at 8-bar intervals.
    """
    if bpm <= 0 or len(onset_env) < 10:
        return []

    frames_per_bar = (sr / hop) * (4 * 60.0 / bpm)
    frames_per_8bars = frames_per_bar * 8

    if frames_per_8bars <= 0:
        return []

    total_bars = int(len(onset_env) / frames_per_bar)

    # Compute energy at each bar boundary, find 8-bar peaks
    boundaries = []
    for bar in range(0, total_bars, 8):
        frame_idx = int(bar * frames_per_bar)
        if frame_idx < len(onset_env):
            boundaries.append(bar)

    return boundaries


def _check_tempo_drift(y: np.ndarray, sr: int, bpm: float) -> tuple[bool, float]:
    """Check for tempo drift (>0.5 BPM variation).

    Returns (has_drift, beat_grid_confidence).
    """
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    _, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)

    if len(beats) < 8:
        return False, 0.5

    beat_times = librosa.frames_to_time(beats, sr=sr)
    ibis = np.diff(beat_times)

    if len(ibis) == 0:
        return False, 0.5

    # Convert IBIs to instantaneous BPM
    inst_bpm = 60.0 / ibis
    bpm_std = float(np.std(inst_bpm))

    has_drift = bpm_std > 0.5
    confidence = max(0.0, min(1.0, 1.0 - bpm_std / 5.0))

    return has_drift, confidence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze(file_path: str, sr: int = 22050) -> TrackFeatures:
    """Analyze an audio file and extract all features.

    Args:
        file_path: Path to audio file (mp3, wav, flac, aiff, m4a).
        sr: Sample rate for analysis (default 22050).

    Returns:
        TrackFeatures with all detected features.
    """
    features = TrackFeatures(file_path=file_path)

    try:
        y, actual_sr = librosa.load(file_path, sr=sr, mono=True)
    except Exception as exc:
        logger.error("Failed to load %s: %s", file_path, exc)
        features.error = str(exc)
        return features

    features.duration_s = float(len(y) / actual_sr)

    # BPM detection
    features.bpm, features.bpm_confidence = _detect_bpm(y, actual_sr)

    # Key detection
    features.key, features.key_confidence = _detect_key(y, actual_sr)

    # Energy and RMS envelope
    features.energy, features.rms_envelope = _detect_energy(y, actual_sr)

    # RMS for intro/outro detection
    rms = librosa.feature.rms(y=y)[0]
    features.intro_bars, features.outro_bars = _detect_intro_outro(rms, features.bpm, actual_sr)

    # Phrase boundaries
    onset_env = librosa.onset.onset_strength(y=y, sr=actual_sr)
    features.phrase_boundaries = _detect_phrase_boundaries(onset_env, features.bpm, actual_sr)

    # Tempo drift / beat grid validation
    features.has_tempo_drift, features.beat_grid_confidence = _check_tempo_drift(y, actual_sr, features.bpm)

    return features


def batch_analyze(directory: str, sr: int = 22050) -> list[TrackFeatures]:
    """Analyze all audio files in a directory.

    Scans for mp3, wav, flac, aiff, m4a files.
    """
    results: list[TrackFeatures] = []
    dir_path = Path(directory)

    if not dir_path.is_dir():
        logger.error("Not a directory: %s", directory)
        return results

    extensions = {".mp3", ".wav", ".flac", ".aiff", ".m4a"}
    files = sorted(f for f in dir_path.rglob("*") if f.suffix.lower() in extensions)

    for i, f in enumerate(files):
        logger.info("Analyzing [%d/%d]: %s", i + 1, len(files), f.name)
        features = analyze(str(f), sr=sr)
        results.append(features)

    return results
