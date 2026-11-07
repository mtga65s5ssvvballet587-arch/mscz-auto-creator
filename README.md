# mscz-auto-creator

Generates MuseScore 4 score files (`.mscz`) from a simple JSON file. It needs only the Python standard library.

## Usage

```bash
pip install -e ".[dev]"
mscz-auto-creator examples/twinkle.json -o twinkle.mscz
# or
PYTHONPATH=src python -m mscz_auto_creator examples/twinkle.json
```

## Input format (JSON)

```json
{
  "title": "Twinkle Twinkle Little Star",
  "composer": "Traditional",
  "tempo": 100,
  "time_signature": "4/4",
  "key": 0,
  "instrument": "piano",
  "measures": [
    ["C4:q", "C4:q", "G4:q", "G4:q"],
    ["C4+E4+G4:w"],
    []
  ]
}
```

| Field | Description |
|---|---|
| `title` / `composer` | Title and composer |
| `tempo` | Tempo in quarter-note BPM (`null` means no tempo marking) |
| `time_signature` | Time signature, e.g. `"3/4"` |
| `key` | Key signature: `-7` to `7` (negative = number of flats, positive = number of sharps) |
| `instrument` | `piano` / `violin` / `flute` / `cello` / `guitar` |
| `clef` | Optional. Overrides the instrument's default clef (`G`, `F`, and so on) |
| `measures` | Array of measures. An empty array `[]` becomes a whole-measure rest |

### Note notation `pitch:duration`

- Pitch: `C4` (middle C), `F#3`, `Bb5`, `C##4`, `Ebb4`
- Rest: `r`
- Chord: join pitches with `+`, e.g. `C4+E4+G4`
- Duration: `w` (whole), `h` (half), `q` (quarter), `8`, `16`, `32`. Add `.` for a dotted note and `..` for a double-dotted note

The total duration of each measure must match the time signature. If it doesn't, the tool raises an error that names the measure number.

## Tests

```bash
pytest
```
