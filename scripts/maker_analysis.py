#!/usr/bin/env python3
"""Validate the auditable handoff from discoveries to maker opportunities."""

from __future__ import annotations

from typing import Any, Mapping

from scripts.maker_opportunity import canonical_url, validate_candidate


class AnalysisValidationError(ValueError):
    """The analysis cannot be traced back to the raw discovery pool."""


def _items(payload: Mapping[str, Any], field: str) -> list[Mapping[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise AnalysisValidationError(f"{field} must be a list")
    if not all(isinstance(item, Mapping) for item in value):
        raise AnalysisValidationError(f"every {field} entry must be an object")
    return value


def validate_analysis_packet(
    raw_payload: Mapping[str, Any],
    analysis_payload: Mapping[str, Any],
    *,
    min_selected: int = 5,
    max_selected: int = 8,
) -> dict[str, Any]:
    """Require a decision for every discovery and evidence-preserving selections."""
    raw_items = _items(raw_payload, "items")
    raw_by_id = {}
    for item in raw_items:
        discovery_id = str(item.get("discovery_id") or "").strip()
        if not discovery_id or discovery_id in raw_by_id:
            raise AnalysisValidationError("raw discoveries need unique discovery_id values")
        raw_by_id[discovery_id] = item

    decision_items = _items(analysis_payload, "decisions")
    decisions = {}
    for item in decision_items:
        discovery_id = str(item.get("discovery_id") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if discovery_id not in raw_by_id or discovery_id in decisions or not reason:
            raise AnalysisValidationError("decisions must uniquely cover known discoveries with reasons")
        selected = item.get("selected")
        if not isinstance(selected, bool):
            raise AnalysisValidationError("decision.selected must be boolean")
        decisions[discovery_id] = {
            "discovery_id": discovery_id,
            "selected": selected,
            "reason": reason,
        }
    if set(decisions) != set(raw_by_id):
        raise AnalysisValidationError("every raw discovery must have exactly one decision")

    opportunities = []
    selected_ids = set()
    for raw_opportunity in _items(analysis_payload, "opportunities"):
        opportunity = validate_candidate(raw_opportunity)
        discovery_id = str(opportunity.get("source_discovery_id") or "").strip()
        if discovery_id not in raw_by_id or discovery_id in selected_ids:
            raise AnalysisValidationError("opportunity needs a unique source_discovery_id")
        raw = raw_by_id[discovery_id]
        if canonical_url(opportunity["url"]) != canonical_url(str(raw.get("url") or "")):
            raise AnalysisValidationError("opportunity URL must match its raw discovery")
        if opportunity["source"] != raw.get("source"):
            raise AnalysisValidationError("opportunity source must match its raw discovery")
        if opportunity["heat_score"] != raw.get("heat_score"):
            raise AnalysisValidationError("analysis cannot change the measured heat score")
        if opportunity["heat_evidence"] != list(raw.get("heat_evidence") or []):
            raise AnalysisValidationError("analysis cannot change measured heat evidence")
        if opportunity["maker_fit_score"] < 3:
            raise AnalysisValidationError("selected opportunities need maker_fit_score >= 3")
        selected_ids.add(discovery_id)
        opportunities.append(opportunity)

    expected_min = min(min_selected, len(raw_items))
    if not expected_min <= len(opportunities) <= min(max_selected, len(raw_items)):
        raise AnalysisValidationError(
            f"selected opportunity count must be between {expected_min} and {min(max_selected, len(raw_items))}"
        )
    decision_selected = {
        discovery_id for discovery_id, decision in decisions.items() if decision["selected"]
    }
    if decision_selected != selected_ids:
        raise AnalysisValidationError("selected decisions must match opportunities exactly")

    return {
        **dict(analysis_payload),
        "opportunities": opportunities,
        "decisions": list(decisions.values()),
    }
