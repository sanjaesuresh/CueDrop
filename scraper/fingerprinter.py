"""ACRCloud audio fingerprinting — identify tracks from audio segments."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FingerprintMatch:
    """A single track match from ACRCloud."""

    title: str
    artist: str
    album: str = ""
    acrid: str = ""
    confidence: float = 0.0  # 0–100
    duration_ms: int = 0
    timestamp_s: float = 0.0  # position in the source audio where this was found


@dataclass
class FingerprintResult:
    """Result of fingerprinting an audio segment."""

    matches: list[FingerprintMatch] = field(default_factory=list)
    status_code: int = 0
    status_msg: str = ""
    success: bool = False
    error: str | None = None


class ACRCloudFingerprinter:
    """Identify tracks using ACRCloud's audio recognition API."""

    def __init__(
        self,
        access_key: str = "",
        access_secret: str = "",
        host: str = "identify-us-west-2.acrcloud.com",
    ) -> None:
        self._access_key = access_key
        self._access_secret = access_secret
        self._host = host
        self._http = httpx.AsyncClient(timeout=30.0)

    @property
    def is_configured(self) -> bool:
        return bool(self._access_key and self._access_secret and self._host)

    def _build_signature(self, timestamp: str) -> str:
        """Build HMAC-SHA1 signature for ACRCloud API."""
        string_to_sign = (
            "POST\n/v1/identify\n"
            + self._access_key + "\n"
            + "audio\n"
            + "1\n"
            + timestamp
        )
        sign = hmac.new(
            self._access_secret.encode("ascii"),
            string_to_sign.encode("ascii"),
            digestmod=hashlib.sha1,
        ).digest()
        return base64.b64encode(sign).decode("ascii")

    async def identify(self, audio_data: bytes) -> FingerprintResult:
        """Identify a track from raw audio bytes.

        Args:
            audio_data: Audio file bytes (WAV, MP3, etc.).

        Returns:
            FingerprintResult with matched tracks.
        """
        result = FingerprintResult()

        if not self.is_configured:
            result.error = "ACRCloud not configured (missing access_key or access_secret)"
            return result

        try:
            timestamp = str(int(time.time()))
            signature = self._build_signature(timestamp)

            data = {
                "access_key": self._access_key,
                "sample_bytes": str(len(audio_data)),
                "timestamp": timestamp,
                "signature": signature,
                "data_type": "audio",
                "signature_version": "1",
            }
            files = {"sample": ("audio.wav", audio_data, "audio/wav")}

            resp = await self._http.post(
                f"https://{self._host}/v1/identify",
                data=data,
                files=files,
            )

            body = resp.json()
            result.status_code = body.get("status", {}).get("code", -1)
            result.status_msg = body.get("status", {}).get("msg", "")

            if result.status_code == 0:
                # Success — parse matches
                music = body.get("metadata", {}).get("music", [])
                for item in music:
                    artists = ", ".join(
                        a.get("name", "") for a in item.get("artists", [])
                    )
                    match = FingerprintMatch(
                        title=item.get("title", ""),
                        artist=artists,
                        album=item.get("album", {}).get("name", ""),
                        acrid=item.get("acrid", ""),
                        confidence=float(item.get("score", 0)),
                        duration_ms=int(item.get("duration_ms", 0)),
                    )
                    result.matches.append(match)
                result.success = True
            elif result.status_code == 1001:
                # No match found — not an error
                result.success = True
            else:
                result.error = result.status_msg

        except Exception as exc:
            logger.error("ACRCloud identify failed: %s", exc)
            result.error = str(exc)

        return result

    async def identify_file(self, file_path: str) -> FingerprintResult:
        """Identify a track from a file path."""
        path = Path(file_path)
        if not path.exists():
            return FingerprintResult(error=f"File not found: {file_path}")

        audio_data = path.read_bytes()
        return await self.identify(audio_data)

    async def scan_at_intervals(
        self,
        file_path: str,
        interval_s: float = 30.0,
        segment_duration_s: float = 10.0,
    ) -> list[FingerprintMatch]:
        """Scan an audio file at regular intervals to build a tracklist.

        Args:
            file_path: Path to audio file.
            interval_s: Seconds between fingerprint checks.
            segment_duration_s: Duration of each audio segment to fingerprint.

        Returns:
            List of FingerprintMatch with timestamp_s set.
        """
        matches: list[FingerprintMatch] = []

        if not self.is_configured:
            logger.warning("ACRCloud not configured — cannot scan")
            return matches

        try:
            import librosa
            import soundfile as sf
            import tempfile

            y, sr = librosa.load(file_path, sr=22050, mono=True)
            total_duration = len(y) / sr

            seen_acrids: set[str] = set()
            timestamp = 0.0

            while timestamp < total_duration:
                # Extract segment
                start_sample = int(timestamp * sr)
                end_sample = int(min(timestamp + segment_duration_s, total_duration) * sr)
                segment = y[start_sample:end_sample]

                if len(segment) < sr:  # less than 1 second
                    break

                # Write segment to temp file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    sf.write(tmp.name, segment, sr)
                    result = await self.identify_file(tmp.name)
                    Path(tmp.name).unlink(missing_ok=True)

                if result.success and result.matches:
                    best = result.matches[0]
                    if best.acrid and best.acrid not in seen_acrids:
                        best.timestamp_s = timestamp
                        matches.append(best)
                        seen_acrids.add(best.acrid)

                timestamp += interval_s

        except ImportError:
            logger.warning("librosa/soundfile not available for interval scanning")
        except Exception as exc:
            logger.error("Interval scan failed: %s", exc)

        return matches

    async def close(self) -> None:
        await self._http.aclose()
