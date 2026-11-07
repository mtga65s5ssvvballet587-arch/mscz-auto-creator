"""Build a MuseScore 4 score (.mscx XML) and pack it into .mscz."""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET

from .notes import DIVISION, Event, NoteError, parse_event

MSCX_VERSION = "4.20"

INSTRUMENTS = {
    # key: (instrumentId, longName, shortName, MIDI program, default clef)
    "piano": ("keyboard.piano", "Piano", "Pno.", 0, "G"),
    "violin": ("strings.violin", "Violin", "Vln.", 40, "G"),
    "flute": ("wind.flutes.flute", "Flute", "Fl.", 73, "G"),
    "cello": ("strings.cello", "Violoncello", "Vc.", 42, "F"),
    "guitar": ("pluck.guitar.nylon-string", "Guitar", "Guit.", 24, "G8vb"),
}


class ScoreError(ValueError):
    """Raised when score data is invalid."""


@dataclass
class ScoreSpec:
    title: str = "Untitled"
    composer: str = ""
    tempo: int | None = 120
    time_signature: tuple[int, int] = (4, 4)
    key: int = 0  # -7..7 (negative = flats, positive = sharps)
    instrument: str = "piano"
    clef: str | None = None
    measures: list[list[str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ScoreSpec":
        ts = data.get("time_signature", "4/4")
        try:
            n, d = (int(x) for x in str(ts).split("/"))
        except ValueError as e:
            raise ScoreError(f"拍子の形式が不正です: {ts!r}（例: 4/4）") from e
        if n <= 0 or d not in (1, 2, 4, 8, 16, 32):
            raise ScoreError(f"拍子の値が不正です: {ts!r}")
        key = int(data.get("key", 0))
        if not -7 <= key <= 7:
            raise ScoreError("key は -7〜7 で指定してください")
        instrument = data.get("instrument", "piano")
        if instrument not in INSTRUMENTS:
            raise ScoreError(f"未対応の楽器です: {instrument!r}（対応: {', '.join(INSTRUMENTS)}）")
        measures = data.get("measures")
        if not measures or not isinstance(measures, list):
            raise ScoreError("measures に1小節以上を指定してください")
        return cls(
            title=str(data.get("title", "Untitled")),
            composer=str(data.get("composer", "")),
            tempo=data.get("tempo", 120),
            time_signature=(n, d),
            key=key,
            instrument=instrument,
            clef=data.get("clef"),
            measures=[list(m) for m in measures],
        )


def _sub(parent: ET.Element, tag: str, text: str | int | None = None, **attrs) -> ET.Element:
    el = ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
    if text is not None:
        el.text = str(text)
    return el


def _write_event(voice: ET.Element, ev: Event) -> None:
    el = _sub(voice, "Rest" if ev.is_rest else "Chord")
    if ev.dots:
        _sub(el, "dots", ev.dots)
    _sub(el, "durationType", ev.duration_type)
    for p in ev.pitches:
        note = _sub(el, "Note")
        _sub(note, "pitch", p.midi)
        _sub(note, "tpc", p.tpc)


def _parse_measures(spec: ScoreSpec) -> list[list[Event]]:
    n, d = spec.time_signature
    capacity = Fraction(n, d)
    parsed: list[list[Event]] = []
    for i, tokens in enumerate(spec.measures, start=1):
        try:
            events = [parse_event(t) for t in tokens]
        except NoteError as e:
            raise ScoreError(f"{i}小節目: {e}") from e
        total = sum((e.length for e in events), Fraction(0))
        if events and total != capacity:
            raise ScoreError(
                f"{i}小節目: 音価の合計 {total} が拍子 {n}/{d}（={capacity}）と一致しません"
            )
        parsed.append(events)
    return parsed


def build_mscx(spec: ScoreSpec) -> bytes:
    measures = _parse_measures(spec)
    inst_id, long_name, short_name, program, default_clef = INSTRUMENTS[spec.instrument]
    clef = spec.clef or default_clef
    n, d = spec.time_signature

    root = ET.Element("museScore", version=MSCX_VERSION)
    score = _sub(root, "Score")
    _sub(score, "Division", DIVISION)
    _sub(score, "metaTag", spec.title, name="workTitle")
    _sub(score, "metaTag", spec.composer, name="composer")

    part = _sub(score, "Part", id=1)
    staff_def = _sub(part, "Staff", id=1)
    st = _sub(staff_def, "StaffType", group="pitched")
    _sub(st, "name", "stdNormal")
    _sub(staff_def, "defaultClef", clef)
    _sub(part, "trackName", long_name)
    inst = _sub(part, "Instrument", id=spec.instrument)
    _sub(inst, "longName", long_name)
    _sub(inst, "shortName", short_name)
    _sub(inst, "trackName", long_name)
    _sub(inst, "instrumentId", inst_id)
    _sub(inst, "clef", clef)
    ch = _sub(inst, "Channel")
    _sub(ch, "program", value=program)

    staff = _sub(score, "Staff", id=1)
    vbox = _sub(staff, "VBox")
    _sub(vbox, "height", 10)
    t = _sub(vbox, "Text")
    _sub(t, "style", "title")
    _sub(t, "text", spec.title)
    if spec.composer:
        c = _sub(vbox, "Text")
        _sub(c, "style", "composer")
        _sub(c, "text", spec.composer)

    for idx, events in enumerate(measures):
        measure = _sub(staff, "Measure")
        voice = _sub(measure, "voice")
        if idx == 0:
            ks = _sub(voice, "KeySig")
            _sub(ks, "concertKey", spec.key)
            ts = _sub(voice, "TimeSig")
            _sub(ts, "sigN", n)
            _sub(ts, "sigD", d)
            if spec.tempo:
                tempo = _sub(voice, "Tempo")
                _sub(tempo, "tempo", f"{float(spec.tempo) / 60:.6g}")  # quarter notes per second
                _sub(tempo, "followText", 1)
                _sub(tempo, "text", f"♩ = {spec.tempo}")
        if events:
            for ev in events:
                _write_event(voice, ev)
        else:  # empty measure -> full-measure rest
            rest = _sub(voice, "Rest")
            _sub(rest, "durationType", "measure")
            _sub(rest, "duration", f"{n}/{d}")

    ET.indent(root, space="  ")
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")


CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="score.mscx"/>
  </rootfiles>
</container>
"""


def write_mscz(spec: ScoreSpec, path: str | Path) -> Path:
    """Write spec to a .mscz (zip) file and return its path."""
    path = Path(path)
    mscx = build_mscx(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("META-INF/container.xml", CONTAINER_XML)
        zf.writestr("score.mscx", mscx)
    return path
