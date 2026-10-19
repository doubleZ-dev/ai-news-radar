import json
from pathlib import Path

from scripts import build_maker_digest


def candidate(title: str = "Desktop robot") -> dict:
    return {
        "title": title,
        "source": "GitHub",
        "url": "https://github.com/example/desktop-robot",
        "published_at": "2026-10-19T00:00:00Z",
        "core_summary": "A small open-source desktop robot.",
        "heat_score": None,
        "heat_evidence": [],
        "maker_fit_score": 5,
        "maker_fit_evidence": ["Printable shell and common modules"],
        "why_for_user": "Matches embedded and 3D-printing skills.",
        "project_idea": "Build an expressive AI desk companion.",
        "minimum_validation": {
            "steps": ["Print one joint and test one servo"],
            "estimated_cost": "CNY 80",
            "estimated_time": "half day",
        },
        "difficulty": "one-day experiment",
        "facts": ["Source files are available"],
        "evidence_links": {"source": ["https://github.com/example/desktop-robot"]},
    }


def test_cli_writes_digest_using_config(tmp_path: Path, monkeypatch):
    source = tmp_path / "candidates.json"
    output = tmp_path / "digest.json"
    config = tmp_path / "config.json"
    source.write_text(json.dumps([candidate()]), encoding="utf-8")
    config.write_text(
        json.dumps(
            {
                "daily_selection": {
                    "min_maker_fit": 4,
                    "max_items": 5,
                    "top_focus_count": 1,
                    "idea_direction_count": 1,
                    "reserve_hidden_gem": True,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_maker_digest.py",
            "--input",
            str(source),
            "--output",
            str(output),
            "--config",
            str(config),
            "--info-gap",
            "YouTube search unavailable",
        ],
    )

    assert build_maker_digest.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["total_items"] == 1
    assert payload["selection_policy"]["max_items"] == 5
    assert payload["info_gaps"] == ["YouTube search unavailable"]
    assert payload["top_focus_ids"] == [payload["items"][0]["opportunity_id"]]
