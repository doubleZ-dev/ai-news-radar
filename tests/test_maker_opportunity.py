from datetime import datetime, timezone

import pytest

from scripts.maker_opportunity import (
    CandidateValidationError,
    build_daily_digest,
    canonical_url,
    select_daily,
    validate_candidate,
)


NOW = datetime(2026, 10, 19, 8, tzinfo=timezone.utc)


def candidate(index=0, **changes):
    base = {
        "title": f"Maker project {index}",
        "source": "Hackaday",
        "url": f"https://example.com/projects/{index}",
        "published_at": NOW.isoformat(),
        "observed_at": NOW.isoformat(),
        "core_summary": "An ESP32 device with a visible physical interaction.",
        "facts": ["The author published firmware and a build video."],
        "community_opinions": [],
        "agent_inferences": ["It could become a desktop companion."],
        "heat_score": 3,
        "heat_evidence": ["The source reports 40 comments in 24 hours."],
        "maker_fit_score": 4,
        "maker_fit_evidence": ["Uses ESP32 and includes printable parts."],
        "why_for_user": "Matches the user's embedded and 3D printing skills.",
        "project_idea": f"Build a status companion variant {index}.",
        "minimum_validation": {
            "steps": ["Connect an ESP32 to one display and render a status."],
            "estimated_cost": "CNY 80",
            "estimated_time": "4 hours",
        },
        "difficulty": "one-day prototype",
        "evidence_links": {
            "code": [f"https://github.com/example/project-{index}"],
            "video": [f"https://youtube.com/watch?v={index}"],
        },
        "risks": [],
    }
    base.update(changes)
    return base


def test_unknown_heat_is_preserved_without_inventing_evidence():
    item = validate_candidate(candidate(heat_score=None, heat_evidence=[]))
    assert item["heat_score"] is None
    assert item["heat_evidence"] == []


def test_known_heat_requires_evidence_and_scores_stay_independent():
    with pytest.raises(CandidateValidationError, match="heat_evidence"):
        validate_candidate(candidate(heat_score=4, heat_evidence=[]))
    with pytest.raises(CandidateValidationError, match="maker_fit_score"):
        validate_candidate(candidate(maker_fit_score=6))
    item = validate_candidate(candidate(heat_score=1, maker_fit_score=5))
    assert item["heat_score"] == 1
    assert item["maker_fit_score"] == 5
    assert "combined_score" not in item


def test_canonical_url_removes_tracking_without_dropping_real_query_values():
    url = canonical_url("https://EXAMPLE.com/project/?utm_source=rss&part=esp32#demo")
    assert url == "https://example.com/project?part=esp32"


def test_selection_is_maker_first_deduplicated_and_never_fills_with_low_fit():
    candidates = [candidate(i, maker_fit_score=5 if i < 2 else 4) for i in range(10)]
    candidates += [
        candidate(20, maker_fit_score=2, heat_score=5),
        candidate(21, url="https://example.com/projects/0?utm_source=copy", maker_fit_score=3),
    ]
    selected = select_daily(candidates)
    assert len(selected) == 8
    assert [item["maker_fit_score"] for item in selected[:2]] == [5, 5]
    assert all(item["maker_fit_score"] >= 3 for item in selected)
    assert len({item["url"] for item in selected}) == len(selected)


def test_high_fit_low_heat_hidden_gem_is_not_lost():
    popular = [candidate(i, maker_fit_score=4, heat_score=5) for i in range(8)]
    hidden = candidate(99, maker_fit_score=4, heat_score=None, heat_evidence=[])
    selected = select_daily(popular + [hidden])
    assert any(item["title"] == hidden["title"] for item in selected)


def test_seen_item_is_suppressed_until_explicit_substantial_update():
    item = validate_candidate(candidate())
    seen = {item["opportunity_id"]: {"status": "saved"}}
    assert select_daily([item], seen=seen) == []
    updated = {**item, "substantial_update": True}
    assert len(select_daily([updated], seen=seen)) == 1


def test_daily_digest_caps_output_and_never_promotes_projects():
    digest = build_daily_digest(
        [candidate(i) for i in range(9)],
        generated_at=NOW,
        info_gaps=["MakerWorld unavailable"],
    )
    assert digest["total_items"] == 8
    assert len(digest["top_focus_ids"]) == 2
    assert len(digest["idea_bank_directions"]) == 2
    assert digest["info_gaps"] == ["MakerWorld unavailable"]
    assert digest["selection_policy"]["heat_is_independent"] is True
    assert digest["selection_policy"]["automatic_project_promotion"] is False
