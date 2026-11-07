"""CLI: python -m mscz_auto_creator input.json -o output.mscz"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .score import ScoreError, ScoreSpec, write_mscz


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mscz-auto-creator", description="JSONからMuseScore(.mscz)を生成")
    ap.add_argument("input", type=Path, help="楽譜データのJSONファイル")
    ap.add_argument("-o", "--output", type=Path, help="出力先 .mscz（省略時は入力名.mscz）")
    args = ap.parse_args(argv)

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        spec = ScoreSpec.from_dict(data)
        out = write_mscz(spec, args.output or args.input.with_suffix(".mscz"))
    except (OSError, json.JSONDecodeError, ScoreError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    print(f"作成しました: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
