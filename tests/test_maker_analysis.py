from datetime import datetime, timezone

import pytest

from scripts.maker_analysis import AnalysisValidationError, validate_analysis_packet
from scripts.maker_opportunity import build_daily_digest
from scripts.render_maker_reports import (
    render_all_discoveries,
    render_curated,
    report_output_dir,
)


NOW = datetime(2026, 10, 19, 8, tzinfo=timezone.utc)


def raw_item(index: int) -> dict:
    return {
        "discovery_id": f"discovery_{index}",
        "source": "Hackaday",
        "title": f"Project {index}",
        "url": f"https://example.com/project/{index}",
        "published_at": NOW.isoformat(),
        "observed_at": NOW.isoformat(),
        "summary": "A build with visible motion.",
        "tags": ["robotics"],
        "metrics": {"comments": index},
        "heat_score": 2,
        "heat_evidence": [f"{index} comments observed"],
    }


def opportunity(item: dict) -> dict:
    return {
        "source_discovery_id": item["discovery_id"],
        "title": item["title"],
        "source": item["source"],
        "url": item["url"],
        "published_at": item["published_at"],
        "observed_at": item["observed_at"],
        "core_summary": "A compact moving device with reusable build details.",
        "facts": ["The source shows a working prototype."],
        "community_opinions": [],
        "agent_inferences": ["A smaller desktop version may be practical."],
        "heat_score": item["heat_score"],
        "heat_evidence": item["heat_evidence"],
        "maker_fit_score": 4,
        "maker_fit_evidence": ["It combines electronics and a printable enclosure."],
        "why_for_user": "It matches embedded, mechanical, and video-making skills.",
        "project_idea": f"Build a desktop variant of project {item['discovery_id']}.",
        "minimum_validation": {
            "steps": ["Prototype one moving axis with an off-the-shelf servo."],
            "estimated_cost": "CNY 60",
            "estimated_time": "4 hours",
        },
        "difficulty": "one-day prototype",
        "evidence_links": {"source": [item["url"]]},
        "risks": ["The enclosure may need two print iterations."],
        "substantial_update": False,
    }


def packet(count: int = 5) -> tuple[dict, dict]:
    items = [raw_item(index) for index in range(count)]
    return (
        {
            "generated_at": NOW.isoformat(),
            "total_items": count,
            "items": items,
            "source_status": [{"source": "Hackaday", "ok": True, "item_count": count}],
            "info_gaps": ["YouTube not yet connected"],
        },
        {
            "opportunities": [opportunity(item) for item in items],
            "decisions": [
                {"discovery_id": item["discovery_id"], "selected": True, "reason": "Strong build potential."}
                for item in items
            ],
            "info_gaps": [],
        },
    )


def test_analysis_requires_a_traceable_decision_for_every_raw_item():
    raw, analysis = packet()
    validated = validate_analysis_packet(raw, analysis)
    assert len(validated["opportunities"]) == 5

    analysis["decisions"].pop()
    with pytest.raises(AnalysisValidationError, match="every raw discovery"):
        validate_analysis_packet(raw, analysis)


def test_analysis_cannot_rewrite_measured_heat_or_source_url():
    raw, analysis = packet()
    analysis["opportunities"][0]["heat_score"] = 5
    with pytest.raises(AnalysisValidationError, match="heat score"):
        validate_analysis_packet(raw, analysis)

    raw, analysis = packet()
    analysis["opportunities"][0]["url"] = "https://example.net/different"
    with pytest.raises(AnalysisValidationError, match="URL"):
        validate_analysis_packet(raw, analysis)


def test_reports_keep_chinese_text_and_every_original_link():
    raw, analysis = packet()
    validated = validate_analysis_packet(raw, analysis)
    digest = build_daily_digest(validated["opportunities"], generated_at=NOW)
    curated = render_curated(digest, raw["source_status"])
    complete = render_all_discoveries(raw, validated)

    assert "每日创客灵感" in curated
    assert "创客匹配" in curated
    assert "全部发现" in complete
    assert "进入精选" in complete
    for item in raw["items"]:
        assert item["url"] in complete


def test_dated_archive_folder_uses_compact_calendar_date(tmp_path):
    assert report_output_dir(tmp_path, "2026-10-19", True) == tmp_path / "20261019"
    assert report_output_dir(tmp_path, "2026-10-19", False) == tmp_path
