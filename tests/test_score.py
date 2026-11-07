import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from mscz_auto_creator import ScoreError, ScoreSpec, build_mscx, write_mscz
from mscz_auto_creator.__main__ import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "twinkle.json"


def spec(**kw):
    data = {"title": "T", "measures": [["C4:q", "D4:q", "E4:h"]]}
    data.update(kw)
    return ScoreSpec.from_dict(data)


def parse(spec_):
    return ET.fromstring(build_mscx(spec_))


def test_root_and_metadata():
    root = parse(spec(composer="Me"))
    assert root.tag == "museScore" and root.get("version") == "4.20"
    tags = {m.get("name"): m.text for m in root.iter("metaTag")}
    assert tags == {"workTitle": "T", "composer": "Me"}


def test_notes_written():
    root = parse(spec())
    pitches = [int(p.text) for p in root.iter("pitch")]
    assert pitches == [60, 62, 64]
    durations = [c.findtext("durationType") for c in root.iter("Chord")]
    assert durations == ["quarter", "quarter", "half"]


def test_first_measure_has_signatures_only():
    root = parse(spec(time_signature="3/4", key=-2, measures=[["C4:h."], ["r:h."]]))
    measures = root.find("Score/Staff").findall("Measure")
    assert len(measures) == 2
    first = measures[0].find("voice")
    assert first.findtext("TimeSig/sigN") == "3" and first.findtext("TimeSig/sigD") == "4"
    assert first.findtext("KeySig/concertKey") == "-2"
    assert measures[1].find("voice/TimeSig") is None
    assert measures[1].find("voice/Rest/durationType").text == "half"


def test_tempo():
    root = parse(spec(tempo=90))
    assert float(root.findtext(".//Tempo/tempo")) == pytest.approx(1.5)


def test_empty_measure_is_measure_rest():
    root = parse(spec(measures=[[]]))
    rest = root.find(".//Measure/voice/Rest")
    assert rest.findtext("durationType") == "measure"
    assert rest.findtext("duration") == "4/4"


def test_dotted_note():
    root = parse(spec(measures=[["C4:h.", "D4:q"]]))
    chord = next(root.iter("Chord"))
    assert chord.findtext("dots") == "1"


def test_instrument_cello_uses_bass_clef():
    root = parse(spec(instrument="cello", measures=[["C3:w"]]))
    assert root.findtext(".//Instrument/instrumentId") == "strings.cello"
    assert root.findtext(".//Part/Staff/defaultClef") == "F"


@pytest.mark.parametrize(
    "kw, msg",
    [
        ({"measures": [["C4:q"]]}, "1小節目"),
        ({"measures": [["C4:w"], ["C4:q", "C4:q"]]}, "2小節目"),
        ({"measures": [["X4:w"]]}, "音名"),
        ({"measures": []}, "measures"),
        ({"time_signature": "4-4"}, "拍子"),
        ({"key": 9}, "key"),
        ({"instrument": "kazoo"}, "楽器"),
    ],
)
def test_validation_errors(kw, msg):
    with pytest.raises(ScoreError, match=msg):
        build_mscx(spec(**kw))


def test_write_mscz_structure(tmp_path):
    out = write_mscz(spec(), tmp_path / "a.mscz")
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "META-INF/container.xml" in names
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        rootfile = container.find("rootfiles/rootfile").get("full-path")
        assert rootfile in names
        ET.fromstring(zf.read(rootfile))  # well-formed


def test_example_file_builds(tmp_path):
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    out = write_mscz(ScoreSpec.from_dict(data), tmp_path / "twinkle.mscz")
    with zipfile.ZipFile(out) as zf:
        root = ET.fromstring(zf.read("score.mscx"))
    assert len(root.findall("Score/Staff/Measure")) == 5
    assert root.findtext(".//VBox/Text/text") == "きらきら星"


def test_cli_success(tmp_path, capsys):
    out = tmp_path / "o.mscz"
    assert main([str(EXAMPLE), "-o", str(out)]) == 0
    assert out.exists() and "作成しました" in capsys.readouterr().out


def test_cli_error(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"measures": [["C4:q"]]}), encoding="utf-8")
    assert main([str(bad)]) == 1
    assert "エラー" in capsys.readouterr().err
