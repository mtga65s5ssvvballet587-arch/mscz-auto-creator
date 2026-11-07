"""mscz-auto-creator: generate MuseScore (.mscz) files from simple JSON."""
from .notes import NoteError, parse_event, parse_pitch
from .score import ScoreError, ScoreSpec, build_mscx, write_mscz

__all__ = [
    "NoteError",
    "ScoreError",
    "ScoreSpec",
    "build_mscx",
    "parse_event",
    "parse_pitch",
    "write_mscz",
]
__version__ = "0.1.0"
