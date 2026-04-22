"""Camelot wheel — harmonic mixing compatibility logic."""

from __future__ import annotations

# Mapping from standard key notation to Camelot code.
_KEY_TO_CAMELOT: dict[str, str] = {
    # Major keys → B codes
    "C": "8B", "Db": "3B", "C#": "3B", "D": "10B", "Eb": "5B", "D#": "5B",
    "E": "12B", "F": "7B", "F#": "2B", "Gb": "2B", "G": "9B",
    "Ab": "4B", "G#": "4B", "A": "11B", "Bb": "6B", "A#": "6B", "B": "1B", "Cb": "1B",
    # Minor keys → A codes
    "Cm": "5A", "C#m": "12A", "Dbm": "12A", "Dm": "7A", "D#m": "2A", "Ebm": "2A",
    "Em": "9A", "Fm": "4A", "F#m": "11A", "Gbm": "11A", "Gm": "6A",
    "G#m": "1A", "Abm": "1A", "Am": "8A", "A#m": "3A", "Bbm": "3A", "Bm": "10A",
}

# All 24 valid Camelot codes
_ALL_CODES = {f"{n}{m}" for n in range(1, 13) for m in ("A", "B")}


def _normalize(key: str) -> str:
    """Normalize a key string to its Camelot code.

    Accepts Camelot codes (e.g. '8A'), standard keys ('Am', 'C'),
    and flat/sharp variants ('Bbm', 'F#').
    """
    key = key.strip()
    # Check if already a Camelot code
    upper_codes = {c.upper(): c for c in _ALL_CODES}
    if key.upper() in upper_codes:
        num = key[:-1]
        letter = key[-1].upper()
        return f"{int(num)}{letter}"
    if key in _KEY_TO_CAMELOT:
        return _KEY_TO_CAMELOT[key]
    raise ValueError(f"Unknown key: {key!r}")


def _parse_code(code: str) -> tuple[int, str]:
    """Parse '8A' into (8, 'A')."""
    return int(code[:-1]), code[-1]


def get_compatible_keys(key: str) -> list[str]:
    """Return all Camelot codes compatible with the given key.

    Compatible moves (Camelot system):
    - Same position (e.g. 8A → 8A)
    - +1 on the wheel (e.g. 8A → 9A)
    - -1 on the wheel (e.g. 8A → 7A)
    - Mode switch (e.g. 8A → 8B)
    """
    code = _normalize(key)
    num, mode = _parse_code(code)

    results = [code]
    # +1
    next_num = num % 12 + 1
    results.append(f"{next_num}{mode}")
    # -1
    prev_num = (num - 2) % 12 + 1
    results.append(f"{prev_num}{mode}")
    # Mode switch
    other_mode = "B" if mode == "A" else "A"
    results.append(f"{num}{other_mode}")

    return results


def is_compatible(key_a: str, key_b: str) -> bool:
    """Check if two keys are harmonically compatible."""
    code_b = _normalize(key_b)
    return code_b in get_compatible_keys(key_a)


def compatibility_score(key_a: str, key_b: str) -> float:
    """Return a 0.0–1.0 score for harmonic compatibility.

    1.0 = same key
    0.75 = adjacent on wheel or mode switch
    0.25 = two steps away
    0.0 = incompatible
    """
    code_a = _normalize(key_a)
    code_b = _normalize(key_b)

    if code_a == code_b:
        return 1.0

    num_a, mode_a = _parse_code(code_a)
    num_b, mode_b = _parse_code(code_b)

    dist = min(abs(num_a - num_b), 12 - abs(num_a - num_b))

    if dist == 1 and mode_a == mode_b:
        return 0.75
    if dist == 0 and mode_a != mode_b:
        return 0.75
    if dist == 2 and mode_a == mode_b:
        return 0.25
    if dist == 1 and mode_a != mode_b:
        return 0.25

    return 0.0
