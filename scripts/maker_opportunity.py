#!/usr/bin/env python3
"""Validate, deduplicate, and select Maker Radar opportunity candidates.

This module deliberately does not fetch sources or call an LLM. It defines the
stable contract between discovery/adapters and the reader-facing daily digest.
Heat and maker fit remain independent: there is no combined score.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


UTC = timezone.utc
DEFAULT_MIN_MAKER_FIT = 3
DEFAULT_MAX_ITEMS = 8
DEFAULT_TOP_FOCUS_COUNT = 2
DEFAULT_IDEA_DIRECTION_COUNT = 2

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}

REQUIRED_TEXT_FIELDS = (
    "title",
    "source",
    "core_summary",
    "why_for_user",
    "project_idea",
    "difficulty",
)


class CandidateValidationError(ValueError):
    """A candidate cannot safely enter the Maker Radar selection stage."""


def canonical_url(value: str) -> str:
    """Return a stable http(s) URL while removing common tracking parameters."""
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise CandidateValidationError("url must be an absolute http(s) URL")
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", urlencode(query), "")
    )


def opportunity_id(candidate: Mapping[str, Any]) -> str:
    basis = canonical_url(str(candidate.get("url") or ""))
    return "maker_" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _score(value: Any, *, field: str, allow_unknown: bool) -> int | None:
    if value is None and allow_unknown:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        suffix = " or null" if allow_unknown else ""
        raise CandidateValidationError(f"{field} must be an integer from 0 to 5{suffix}")
    if not 0 <= value <= 5:
        raise CandidateValidationError(f"{field} must be between 0 and 5")
    return value


def _text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise CandidateValidationError(f"{field} is required")
    return text


def _text_list(value: Any, field: str, *, required: bool = False) -> list[str]:
    if value is None:
        value = []
    if not isinstance(value, list):
        raise CandidateValidationError(f"{field} must be a list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if required and not result:
        raise CandidateValidationError(f"{field} must contain at least one item")
    return result


def _timestamp(value: Any) -> float:
    if not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.timestamp()
    except (TypeError, ValueError):
        return 0.0


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize and validate one opportunity without inventing missing facts."""
    if not isinstance(candidate, Mapping):
        raise CandidateValidationError("candidate must be an object")

    out = deepcopy(dict(candidate))
    for field in REQUIRED_TEXT_FIELDS:
        out[field] = _text(out.get(field), field)

    out["url"] = canonical_url(_text(out.get("url"), "url"))
    out["published_at"] = str(out.get("published_at") or "").strip() or None
    out["observed_at"] = str(out.get("observed_at") or "").strip() or None
    if not out["published_at"] and not out["observed_at"]:
        raise CandidateValidationError("published_at or observed_at is required")

    out["heat_score"] = _score(out.get("heat_score"), field="heat_score", allow_unknown=True)
    out["maker_fit_score"] = _score(
        out.get("maker_fit_score"), field="maker_fit_score", allow_unknown=False
    )
    out["heat_evidence"] = _text_list(out.get("heat_evidence"), "heat_evidence")
    if out["heat_score"] is not None and not out["heat_evidence"]:
        raise CandidateValidationError("heat_evidence is required when heat_score is known")
    out["maker_fit_evidence"] = _text_list(
        out.get("maker_fit_evidence"), "maker_fit_evidence", required=True
    )
    out["facts"] = _text_list(out.get("facts"), "facts", required=True)
    out["community_opinions"] = _text_list(
        out.get("community_opinions"), "community_opinions"
    )
    out["agent_inferences"] = _text_list(out.get("agent_inferences"), "agent_inferences")
    out["risks"] = _text_list(out.get("risks"), "risks")

    validation = out.get("minimum_validation")
    if not isinstance(validation, Mapping):
        raise CandidateValidationError("minimum_validation must be an object")
    steps = _text_list(validation.get("steps"), "minimum_validation.steps", required=True)
    out["minimum_validation"] = {
        **deepcopy(dict(validation)),
        "steps": steps,
        "estimated_cost": str(validation.get("estimated_cost") or "unknown").strip(),
        "estimated_time": str(validation.get("estimated_time") or "unknown").strip(),
    }

    evidence_links = out.get("evidence_links") or {}
    if not isinstance(evidence_links, Mapping):
        raise CandidateValidationError("evidence_links must be an object")
    out["evidence_links"] = {
        str(kind): _text_list(links, f"evidence_links.{kind}")
        for kind, links in evidence_links.items()
    }

    out["substantial_update"] = bool(out.get("substantial_update", False))
    out["opportunity_id"] = str(out.get("opportunity_id") or opportunity_id(out))
    return out


def evidence_count(candidate: Mapping[str, Any]) -> int:
    links = candidate.get("evidence_links") or {}
    if not isinstance(links, Mapping):
        return 0
    return sum(len(value) for value in links.values() if isinstance(value, list))


def deduplicate_candidates(candidates: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Collapse URL duplicates, keeping the richer/higher-fit representation."""
    by_url: dict[str, dict[str, Any]] = {}
    for raw in candidates:
        candidate = validate_candidate(raw)
        url = candidate["url"]
        current = by_url.get(url)
        if current is None:
            by_url[url] = candidate
            continue
        new_key = (candidate["maker_fit_score"], evidence_count(candidate), len(candidate["facts"]))
        old_key = (current["maker_fit_score"], evidence_count(current), len(current["facts"]))
        if new_key > old_key:
            by_url[url] = candidate
    return list(by_url.values())


def _selection_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    heat = candidate.get("heat_score")
    observed = candidate.get("published_at") or candidate.get("observed_at")
    return (
        -int(candidate["maker_fit_score"]),
        -evidence_count(candidate),
        1 if heat is None else 0,
        -int(heat or 0),
        -_timestamp(observed),
        str(candidate["title"]).lower(),
    )


def _seen_entry(
    candidate: Mapping[str, Any], seen: Mapping[str, Mapping[str, Any]] | None
) -> Mapping[str, Any] | None:
    if not seen:
        return None
    return seen.get(str(candidate["opportunity_id"]))


def select_daily(
    candidates: Iterable[Mapping[str, Any]],
    *,
    seen: Mapping[str, Mapping[str, Any]] | None = None,
    min_maker_fit: int = DEFAULT_MIN_MAKER_FIT,
    max_items: int = DEFAULT_MAX_ITEMS,
    reserve_hidden_gem: bool = True,
) -> list[dict[str, Any]]:
    """Select up to eight opportunities, led by maker fit rather than heat."""
    if not 0 <= min_maker_fit <= 5:
        raise ValueError("min_maker_fit must be between 0 and 5")
    if not 1 <= max_items <= DEFAULT_MAX_ITEMS:
        raise ValueError(f"max_items must be between 1 and {DEFAULT_MAX_ITEMS}")

    eligible = []
    for candidate in deduplicate_candidates(candidates):
        if candidate["maker_fit_score"] < min_maker_fit:
            continue
        previous = _seen_entry(candidate, seen)
        if previous and not candidate["substantial_update"]:
            continue
        eligible.append(candidate)

    ranked = sorted(eligible, key=_selection_key)
    selected = ranked[:max_items]

    # Guarantee that a high-fit, low/unknown-heat discovery is not crowded out
    # by popular items. This does not fabricate a heat value or combined score.
    hidden = [
        item
        for item in ranked
        if item["maker_fit_score"] >= 4
        and (item["heat_score"] is None or item["heat_score"] <= 2)
    ]
    if reserve_hidden_gem and hidden and selected and hidden[0] not in selected:
        selected[-1] = hidden[0]
        selected = sorted(selected, key=_selection_key)
    return selected


def build_daily_digest(
    candidates: Iterable[Mapping[str, Any]],
    *,
    generated_at: datetime | None = None,
    seen: Mapping[str, Mapping[str, Any]] | None = None,
    info_gaps: Iterable[str] = (),
    min_maker_fit: int = DEFAULT_MIN_MAKER_FIT,
    max_items: int = DEFAULT_MAX_ITEMS,
    reserve_hidden_gem: bool = True,
    top_focus_count: int = DEFAULT_TOP_FOCUS_COUNT,
    idea_direction_count: int = DEFAULT_IDEA_DIRECTION_COUNT,
) -> dict[str, Any]:
    """Build the first stable Maker Radar JSON payload."""
    now = generated_at or datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    if not 0 <= top_focus_count <= max_items:
        raise ValueError("top_focus_count must be between 0 and max_items")
    if not 0 <= idea_direction_count <= max_items:
        raise ValueError("idea_direction_count must be between 0 and max_items")
    selected = select_daily(
        candidates,
        seen=seen,
        min_maker_fit=min_maker_fit,
        max_items=max_items,
        reserve_hidden_gem=reserve_hidden_gem,
    )
    ideas = []
    for item in selected:
        idea = item["project_idea"]
        if idea not in ideas:
            ideas.append(idea)
        if len(ideas) == idea_direction_count:
            break
    return {
        "schema_version": 1,
        "generated_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "total_items": len(selected),
        "items": selected,
        "top_focus_ids": [
            item["opportunity_id"] for item in selected[:top_focus_count]
        ],
        "idea_bank_directions": ideas,
        "info_gaps": [str(gap).strip() for gap in info_gaps if str(gap).strip()],
        "selection_policy": {
            "primary_signal": "maker_fit",
            "heat_is_independent": True,
            "unknown_heat_allowed": True,
            "max_items": max_items,
            "automatic_project_promotion": False,
        },
    }
