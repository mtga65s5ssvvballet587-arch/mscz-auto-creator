"""Note token parsing: "C4:q", "F#3:8.", "C4+E4+G4:h", "r:w"."""
from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

DIVISION = 480  # ticks per quarter note (MuseScore default)

DURATIONS = {
    "w": ("whole", Fraction(1, 1)),
    "h": ("half", Fraction(1, 2)),
    "q": ("quarter", Fraction(1, 4)),
    "8": ("eighth", Fraction(1, 8)),
    "16": ("16th", Fraction(1, 16)),
    "32": ("32nd", Fraction(1, 32)),
}

_STEP_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Tonal pitch class of natural letters (MuseScore convention: C = 14)
_STEP_TPC = {"F": 13, "C": 14, "G": 15, "D": 16, "A": 17, "E": 18, "B": 19}
_ACCIDENTALS = {"": 0, "#": 1, "##": 2, "b": -1, "bb": -2}

_PITCH_RE = re.compile(r"^([A-Ga-g])(##|#|bb|b)?(-?\d)$")


class NoteError(ValueError):
    """Raised when a note token cannot be parsed."""


@dataclass(frozen=True)
class Pitch:
    midi: int
    tpc: int


@dataclass(frozen=True)
class Event:
    """A chord (one or more pitches) or a rest (no pitches)."""

    pitches: tuple[Pitch, ...]
    duration_type: str
    dots: int
    length: Fraction  # in whole notes

    @property
    def is_rest(self) -> bool:
        return not self.pitches


def parse_pitch(text: str) -> Pitch:
    m = _PITCH_RE.match(text.strip())
    if not m:
        raise NoteError(f"音名を解釈できません: {text!r}（例: C4, F#3, Bb5）")
    step, acc, octave = m.group(1).upper(), m.group(2) or "", int(m.group(3))
    alter = _ACCIDENTALS[acc]
    midi = 12 * (octave + 1) + _STEP_SEMITONE[step] + alter
    if not 0 <= midi <= 127:
        raise NoteError(f"音域外の音です: {text!r}")
    return Pitch(midi=midi, tpc=_STEP_TPC[step] + 7 * alter)


def parse_duration(text: str) -> tuple[str, int, Fraction]:
    base = text.rstrip(".")
    dots = len(text) - len(base)
    if base not in DURATIONS or dots > 2:
        raise NoteError(f"音価を解釈できません: {text!r}（w, h, q, 8, 16, 32 と付点 .）")
    name, length = DURATIONS[base]
    total = length * (2 - Fraction(1, 2**dots))
    return name, dots, total


def parse_event(token: str) -> Event:
    if ":" not in token:
        raise NoteError(f"'音名:音価' の形式で書いてください: {token!r}")
    pitch_part, dur_part = token.rsplit(":", 1)
    name, dots, length = parse_duration(dur_part.strip())
    pitch_part = pitch_part.strip()
    if pitch_part.lower() == "r":
        pitches: tuple[Pitch, ...] = ()
    else:
        pitches = tuple(sorted((parse_pitch(p) for p in pitch_part.split("+")), key=lambda p: p.midi))
    return Event(pitches=pitches, duration_type=name, dots=dots, length=length)
