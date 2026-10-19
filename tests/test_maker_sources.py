from datetime import datetime, timedelta, timezone

from scripts.collect_maker_candidates import collect_all
from scripts.maker_sources import parse_github_source, parse_hn_payloads, parse_rss_source


NOW = datetime(2026, 10, 19, 8, tzinfo=timezone.utc)


def source(source_id="hackaday", source_type="rss", **changes):
    value = {
        "id": source_id,
        "name": "Hackaday",
        "type": source_type,
        "category": "maker_open_source",
        "url": "https://hackaday.com/feed/",
        "allowed_hosts": ["hackaday.com"],
        "window_hours": 72,
        **changes,
    }
    return value


def test_rss_preserves_time_evidence_and_unknown_heat():
    recent = (NOW - timedelta(hours=2)).isoformat()
    stale = (NOW - timedelta(days=4)).isoformat()
    xml = f"""<rss xmlns:slash="http://purl.org/rss/1.0/modules/slash/"><channel>
      <item><title>ESP32 E-Ink Desk Companion</title><link>https://hackaday.com/desk/</link>
      <pubDate>{recent}</pubDate><description>3D printed case and sensor</description></item>
      <item><title>Old Robot</title><link>https://hackaday.com/old/</link>
      <pubDate>{stale}</pubDate></item></channel></rss>"""
    items = parse_rss_source(xml, source(), NOW)
    assert len(items) == 1
    assert items[0]["tags"] == ["3d-printing", "embedded", "interaction"]
    assert items[0]["heat_score"] is None
    assert items[0]["published_at"] == "2026-10-19T06:00:00Z"
    assert items[0]["analysis_state"] == "pending"


def test_rss_uses_comment_count_as_verifiable_heat():
    recent = (NOW - timedelta(hours=2)).isoformat()
    xml = f"""<rss xmlns:slash="http://purl.org/rss/1.0/modules/slash/"><channel><item>
      <title>Robot</title><link>https://hackaday.com/robot/</link><pubDate>{recent}</pubDate>
      <slash:comments>18</slash:comments></item></channel></rss>"""
    item = parse_rss_source(xml, source(), NOW)[0]
    assert item["heat_score"] == 3
    assert item["heat_evidence"] == ["comments: 18"]


def test_github_filters_non_maker_repositories_and_keeps_stars():
    html = """<article class="Box-row"><h2><a href="/team/robot">team/robot</a></h2>
      <p>ESP32 open source desktop robot</p><span>123 stars today</span></article>
      <article class="Box-row"><h2><a href="/team/billing">team/billing</a></h2>
      <p>Enterprise invoicing SaaS</p><span>900 stars today</span></article>"""
    items = parse_github_source(html, source("github_trending", "github_trending", name="GitHub Trending"), NOW)
    assert [item["title"] for item in items] == ["team/robot"]
    assert items[0]["metrics"]["stars_today"] == 123
    assert items[0]["heat_score"] == 2


def test_hn_deduplicates_queries_and_keeps_discussion_evidence():
    hit = {
        "objectID": "42",
        "title": "Show HN: Open source robot arm",
        "url": "https://example.com/robot",
        "created_at": (NOW - timedelta(hours=1)).isoformat(),
        "points": 20,
        "num_comments": 10,
    }
    irrelevant = {**hit, "objectID": "43", "title": "A knowledge graph that re-reads code"}
    near_match = {**hit, "objectID": "44", "title": "CADR Mono programming font"}
    items = parse_hn_payloads(
        [("robotics", {"hits": [hit, irrelevant, near_match]}), ("open source hardware", {"hits": [hit]})],
        source("hackernews_maker", "hn_algolia", name="Hacker News"),
        NOW,
    )
    assert len(items) == 1
    assert items[0]["heat_score"] == 4
    assert items[0]["evidence_links"]["discussion"] == ["https://news.ycombinator.com/item?id=42"]


def test_collection_failure_is_visible_without_losing_healthy_source():
    class Response:
        text = "<rss><channel><item><title>ESP32</title><link>https://hackaday.com/x/</link>" \
            f"<pubDate>{NOW.isoformat()}</pubDate></item></channel></rss>"

        def raise_for_status(self):
            return None

    class Session:
        def get(self, url, **_kwargs):
            if "broken" in url:
                raise RuntimeError("offline")
            return Response()

    config = {
        "sources": [source(), source("broken", url="https://broken.example/feed")],
        "declared_gaps": ["MakerWorld unavailable"],
    }
    payload = collect_all(Session(), config, NOW)
    assert payload["total_items"] == 1
    assert [status["ok"] for status in payload["source_status"]] == [True, False]
    assert any("offline" in gap for gap in payload["info_gaps"])
