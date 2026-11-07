from fractions import Fraction

import pytest

from mscz_auto_creator.notes import NoteError, parse_duration, parse_event, parse_pitch


@pytest.mark.parametrize(
    "text, midi, tpc",
    [
        ("C4", 60, 14),
        ("A4", 69, 17),
        ("C#4", 61, 21),
        ("Db4", 61, 9),
        ("Bb3", 58, 12),
        ("F#5", 78, 20),
        ("C-1", 0, 14),
    ],
)
def test_parse_pitch(text, midi, tpc):
    p = parse_pitch(text)
    assert (p.midi, p.tpc) == (midi, tpc)


@pytest.mark.parametrize("bad", ["H4", "C", "C#", "Cx4", "G#9"])
def test_parse_pitch_invalid(bad):
    with pytest.raises(NoteError):
        parse_pitch(bad)


@pytest.mark.parametrize(
    "text, name, dots, length",
    [
        ("w", "whole", 0, Fraction(1)),
        ("q", "quarter", 0, Fraction(1, 4)),
        ("q.", "quarter", 1, Fraction(3, 8)),
        ("h..", "half", 2, Fraction(7, 8)),
        ("16", "16th", 0, Fraction(1, 16)),
    ],
)
def test_parse_duration(text, name, dots, length):
    assert parse_duration(text) == (name, dots, length)


@pytest.mark.parametrize("bad", ["x", "q...", "64", ""])
def test_parse_duration_invalid(bad):
    with pytest.raises(NoteError):
        parse_duration(bad)


def test_parse_rest():
    ev = parse_event("r:h")
    assert ev.is_rest and ev.length == Fraction(1, 2)


def test_parse_chord_sorted():
    ev = parse_event("G4+C4+E4:w")
    assert [p.midi for p in ev.pitches] == [60, 64, 67]


def test_parse_event_requires_colon():
    with pytest.raises(NoteError):
        parse_event("C4q")
