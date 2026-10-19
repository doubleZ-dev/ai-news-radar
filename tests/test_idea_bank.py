from datetime import datetime, timezone

import pytest

from scripts.idea_bank import apply_user_action, bank_index, empty_bank, load_bank, save_bank


NOW = datetime(2026, 10, 19, 8, tzinfo=timezone.utc)


def candidate():
    return {
        "title": "ESP32 e-paper companion",
        "source": "GitHub",
        "url": "https://github.com/example/epaper-companion",
        "published_at": NOW.isoformat(),
        "core_summary": "An open-source ESP32 e-paper desktop display.",
        "facts": ["Firmware is available."],
        "heat_score": None,
        "heat_evidence": [],
        "maker_fit_score": 5,
        "maker_fit_evidence": ["Matches ESP32 and 3D printing skills."],
        "why_for_user": "It can be remixed into a desktop companion.",
        "project_idea": "Build a USB status companion with swappable faces.",
        "minimum_validation": {"steps": ["Render one status on an e-paper panel."]},
        "difficulty": "one-day prototype",
        "evidence_links": {"code": ["https://github.com/example/epaper-companion"]},
    }


@pytest.mark.parametrize(
    ("action", "status"),
    [("save", "saved"), ("ignore", "ignored"), ("research", "research_candidate")],
)
def test_only_user_facing_actions_change_idea_bank(action, status):
    bank = apply_user_action(empty_bank(), candidate(), action, acted_at=NOW)
    item = next(iter(bank_index(bank).values()))
    assert item["status"] == status
    assert item["history"][-1]["action"] == action


def test_high_score_cannot_automatically_promote_to_project():
    with pytest.raises(ValueError, match="unsupported Idea Bank action"):
        apply_user_action(empty_bank(), candidate(), "promote", acted_at=NOW)


def test_bank_round_trip_is_utf8_and_updates_existing_entry(tmp_path):
    first = apply_user_action(empty_bank(), candidate(), "save", acted_at=NOW)
    second = apply_user_action(first, candidate(), "research", acted_at=NOW)
    assert len(second["items"]) == 1
    assert len(second["items"][0]["history"]) == 2
    path = tmp_path / "idea-bank.json"
    save_bank(path, second)
    loaded = load_bank(path)
    assert loaded == second
