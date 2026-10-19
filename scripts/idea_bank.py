#!/usr/bin/env python3
"""Local, user-controlled Idea Bank storage for Maker Inspiration Radar."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from scripts.maker_opportunity import validate_candidate


UTC = timezone.utc
ACTION_TO_STATUS = {
    "save": "saved",
    "ignore": "ignored",
    "research": "research_candidate",
}
VALID_STATUSES = {
    "new",
    "saved",
    "ignored",
    "research_candidate",
    "researched",
    "promoted_to_project",
}


def empty_bank() -> dict[str, Any]:
    return {"schema_version": 1, "updated_at": None, "items": []}


def load_bank(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return empty_bank()
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Idea Bank must be an object with an items list")
    return payload


def save_bank(path: str | Path, bank: Mapping[str, Any]) -> None:
    """Write atomically so an interrupted run cannot destroy the user's bank."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(target)


def bank_index(bank: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item.get("opportunity_id")): item
        for item in bank.get("items", [])
        if isinstance(item, Mapping) and item.get("opportunity_id")
    }


def apply_user_action(
    bank: Mapping[str, Any],
    raw_candidate: Mapping[str, Any],
    action: str,
    *,
    acted_at: datetime | None = None,
) -> dict[str, Any]:
    """Apply only explicit save/ignore/research actions.

    Project promotion is intentionally absent. It requires a separate explicit
    user workflow and can never be inferred from a high score.
    """
    if action not in ACTION_TO_STATUS:
        allowed = ", ".join(sorted(ACTION_TO_STATUS))
        raise ValueError(f"unsupported Idea Bank action; expected one of: {allowed}")
    candidate = validate_candidate(raw_candidate)
    now = acted_at or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    timestamp = now.astimezone(UTC).isoformat().replace("+00:00", "Z")

    out = deepcopy(dict(bank))
    out.setdefault("schema_version", 1)
    items = [deepcopy(item) for item in out.get("items", [])]
    existing = next(
        (item for item in items if item.get("opportunity_id") == candidate["opportunity_id"]),
        None,
    )
    event = {"action": action, "status": ACTION_TO_STATUS[action], "acted_at": timestamp}
    if existing is None:
        existing = {
            "opportunity_id": candidate["opportunity_id"],
            "title": candidate["title"],
            "url": candidate["url"],
            "first_seen_at": timestamp,
            "history": [],
        }
        items.append(existing)
    existing.update(
        {
            "title": candidate["title"],
            "url": candidate["url"],
            "status": ACTION_TO_STATUS[action],
            "last_seen_at": timestamp,
            "maker_fit_score": candidate["maker_fit_score"],
            "heat_score": candidate["heat_score"],
            "project_idea": candidate["project_idea"],
        }
    )
    existing.setdefault("history", []).append(event)
    out["items"] = items
    out["updated_at"] = timestamp
    return out
