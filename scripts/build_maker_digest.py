#!/usr/bin/env python3
"""Build a Maker Inspiration Radar digest from normalized candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.idea_bank import bank_index, load_bank
from scripts.maker_opportunity import build_daily_digest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "maker-radar.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    raise ValueError("candidate input must be a list or an object with an items list")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Normalized candidate JSON")
    parser.add_argument("--output", required=True, type=Path, help="Digest JSON to write")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--idea-bank", type=Path, help="Optional local Idea Bank JSON")
    parser.add_argument(
        "--info-gap", action="append", default=[], help="Uncovered source or uncertainty"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = read_json(args.config)
    daily = config.get("daily_selection", {})
    seen = bank_index(load_bank(args.idea_bank)) if args.idea_bank else None
    digest = build_daily_digest(
        candidate_items(read_json(args.input)),
        seen=seen,
        info_gaps=args.info_gap,
        min_maker_fit=int(daily.get("min_maker_fit", 3)),
        max_items=int(daily.get("max_items", 8)),
        reserve_hidden_gem=bool(daily.get("reserve_hidden_gem", True)),
        top_focus_count=int(daily.get("top_focus_count", 2)),
        idea_direction_count=int(daily.get("idea_direction_count", 2)),
    )
    write_json(args.output, digest)
    print(f"Wrote: {args.output} ({digest['total_items']} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
