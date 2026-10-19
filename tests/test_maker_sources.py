from datetime import datetime, timedelta, timezone

import pytest

from scripts.collect_maker_candidates import collect_all
from scripts.maker_sources import (
    parse_github_source,
    parse_hn_payloads,
    parse_follow_builders_x,
    parse_huggingface_daily,
    parse_producthunt_source,
    parse_rss_source,
    parse_youtube_source,
)


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


def test_rss_bytes_preserve_utf8_punctuation():
    recent = (NOW - timedelta(hours=2)).isoformat()
    xml = f"""<?xml version="1.0" encoding="UTF-8"?><rss><channel><item>
      <title>Robot — small but expressive</title><link>https://hackaday.com/utf8/</link>
      <pubDate>{recent}</pubDate><description>Maker’s test…</description>
      </item></channel></rss>""".encode("utf-8")
    item = parse_rss_source(xml, source(), NOW)[0]
    assert item["title"] == "Robot — small but expressive"
    assert item["summary"] == "Maker’s test…"


def test_rss_uses_comment_count_as_verifiable_heat():
    recent = (NOW - timedelta(hours=2)).isoformat()
    xml = f"""<rss xmlns:slash="http://purl.org/rss/1.0/modules/slash/"><channel><item>
      <title>Robot</title><link>https://hackaday.com/robot/</link><pubDate>{recent}</pubDate>
      <slash:comments>18</slash:comments></item></channel></rss>"""
    item = parse_rss_source(xml, source(), NOW)[0]
    assert item["heat_score"] == 3
    assert item["heat_evidence"] == ["comments: 18"]


def test_youtube_uses_upload_time_and_preserves_views_as_heat_evidence():
    recent = (NOW - timedelta(hours=2)).isoformat()
    edited = (NOW - timedelta(hours=1)).isoformat()
    stale = (NOW - timedelta(days=20)).isoformat()
    xml = f'''<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/">
      <entry><yt:videoId>recent</yt:videoId><title>ESP32 Robot Build</title>
        <link rel="alternate" href="https://www.youtube.com/watch?v=recent"/>
        <published>{recent}</published><updated>{edited}</updated>
        <media:group><media:description>3D printed desktop robot</media:description>
        <media:community><media:starRating count="2500" average="5.00" min="1" max="5"/>
        <media:statistics views="60000"/></media:community></media:group></entry>
      <entry><yt:videoId>stale</yt:videoId><title>Old Robot</title>
        <link rel="alternate" href="https://www.youtube.com/watch?v=stale"/>
        <published>{stale}</published><updated>{edited}</updated></entry>
    </feed>'''
    items = parse_youtube_source(
        xml,
        source(
            "youtube_maker",
            "youtube_rss",
            name="YouTube · Maker",
            url="https://www.youtube.com/feeds/videos.xml?channel_id=test",
            allowed_hosts=["www.youtube.com"],
            category="creative_video",
            default_tags=["creative-video"],
            window_hours=168,
        ),
        NOW,
    )
    assert len(items) == 1
    assert items[0]["published_at"] == "2026-10-19T06:00:00Z"
    assert items[0]["metrics"] == {"views": 60000, "ratings": 2500}
    assert items[0]["heat_score"] == 3
    assert items[0]["heat_evidence"] == ["YouTube views: 60000"]
    assert "creative-video" in items[0]["tags"]


def test_curated_rss_can_add_source_tags_and_cap_items():
    recent = (NOW - timedelta(hours=2)).isoformat()
    xml = f"""<rss><channel>
      <item><title>Build one</title><link>https://hackaday.com/one/</link><pubDate>{recent}</pubDate></item>
      <item><title>Build two</title><link>https://hackaday.com/two/</link><pubDate>{recent}</pubDate></item>
    </channel></rss>"""
    items = parse_rss_source(
        xml, source(default_tags=["creative-video"], max_items=1), NOW
    )
    assert len(items) == 1
    assert items[0]["tags"] == ["creative-video"]


def test_curated_rss_can_require_maker_signal_before_default_tags():
    recent = (NOW - timedelta(hours=2)).isoformat()
    xml = f"""<rss><channel>
      <item><title>NOAA winter outlook</title><link>https://hackaday.com/weather/</link><pubDate>{recent}</pubDate></item>
      <item><title>Chainable LED pixel</title><link>https://hackaday.com/led/</link><pubDate>{recent}</pubDate></item>
    </channel></rss>"""
    items = parse_rss_source(
        xml,
        source(
            default_tags=["vendor-blog"],
            require_maker_tags=True,
            max_items=5,
        ),
        NOW,
    )
    assert [item["title"] for item in items] == ["Chainable LED pixel"]
    assert items[0]["tags"] == ["interaction", "vendor-blog"]


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


def test_producthunt_reuses_verified_feed_parser_and_filters_for_maker_value():
    xml = f'''<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Robot Bench</title><link href="https://www.producthunt.com/products/robot-bench"/>
      <published>{NOW.isoformat()}</published><updated>{NOW.isoformat()}</updated>
      <content type="html">3D printing and ESP32 robot prototyping</content></entry>
      <entry><title>Finance App</title><link href="https://www.producthunt.com/products/finance-app"/>
      <published>{NOW.isoformat()}</published><updated>{NOW.isoformat()}</updated>
      <content type="html">Corporate invoice management</content></entry>
    </feed>'''
    items = parse_producthunt_source(
        xml,
        source("producthunt_maker", "producthunt", name="Product Hunt", category="new_products_trends"),
        NOW,
    )
    assert [item["title"] for item in items] == ["Robot Bench"]
    assert items[0]["heat_score"] is None
    assert items[0]["published_at"] == "2026-10-19T08:00:00Z"


def test_huggingface_daily_requires_focus_term_and_keeps_real_engagement():
    payload = [
        {
            "paper": {
                "id": "2610.12345",
                "title": "Tactile Robot Hand",
                "ai_summary": "A low-cost tactile sensor for manipulation.",
                "submittedOnDailyAt": NOW.isoformat(),
                "upvotes": 8,
                "githubStars": 20,
                "githubRepo": "https://github.com/example/tactile-hand",
                "ai_keywords": ["robot", "tactile"],
            },
            "numComments": 3,
        },
        {
            "paper": {
                "id": "2610.99999",
                "title": "Language model finance benchmark",
                "ai_summary": "A text-only benchmark.",
                "submittedOnDailyAt": NOW.isoformat(),
            }
        },
    ]
    items = parse_huggingface_daily(
        payload,
        source(
            "huggingface_daily_maker",
            "huggingface_daily",
            name="Hugging Face Daily Papers",
            category="frontier_research",
            focus_terms=["robot", "tactile"],
        ),
        NOW,
    )
    assert len(items) == 1
    assert items[0]["url"] == "https://huggingface.co/papers/2610.12345"
    assert items[0]["metrics"] == {
        "upvotes": 8,
        "comments": 3,
        "github_stars": 20,
        "project_page": "",
        "github_repo": "https://github.com/example/tactile-hand",
    }
    assert items[0]["heat_evidence"] == [
        "HF engagement (upvotes + 2×comments + capped GitHub stars): 34"
    ]


def test_follow_builders_x_filters_non_maker_posts_and_preserves_metrics():
    payload = {
        "generatedAt": NOW.isoformat(),
        "x": [
            {
                "name": "Builder",
                "handle": "builder",
                "bio": "Open hardware projects",
                "tweets": [
                    {
                        "id": "1",
                        "text": "Built an ESP32 haptic robot controller",
                        "createdAt": (NOW - timedelta(hours=1)).isoformat(),
                        "url": "https://x.com/builder/status/1",
                        "likes": 20,
                        "retweets": 4,
                        "replies": 3,
                    },
                    {
                        "id": "2",
                        "text": "Quarterly finance results",
                        "createdAt": (NOW - timedelta(hours=1)).isoformat(),
                        "url": "https://x.com/builder/status/2",
                        "likes": 100,
                        "retweets": 20,
                        "replies": 10,
                    },
                ],
            }
        ],
    }
    items = parse_follow_builders_x(
        payload,
        source(
            "follow_builders_x_maker",
            "follow_builders_x",
            name="X · Follow Builders",
            category="community_trends",
        ),
        NOW,
    )
    assert len(items) == 1
    assert items[0]["metrics"]["handle"] == "builder"
    assert items[0]["heat_evidence"] == [
        "X engagement (likes + 2×reposts + replies): 31"
    ]
    assert items[0]["heat_score"] == 3


def test_follow_builders_x_rejects_invalid_payload_as_source_failure():
    with pytest.raises(ValueError, match="invalid X feed"):
        parse_follow_builders_x({}, source(name="X · Follow Builders"), NOW)


def test_collection_failure_is_visible_without_losing_healthy_source():
    class Response:
        text = "<rss><channel><item><title>ESP32</title><link>https://hackaday.com/x/</link>" \
            f"<pubDate>{NOW.isoformat()}</pubDate></item></channel></rss>"
        content = text.encode("utf-8")

        def raise_for_status(self):
            return None

    class Session:
        def get(self, url, **_kwargs):
            if "broken" in url:
                raise RuntimeError("offline")
            return Response()

    config = {
        "sources": [
            source(),
            source("broken", url="https://broken.example/feed"),
            source("disabled", enabled=False, disabled_reason="not stable"),
        ],
        "declared_gaps": ["MakerWorld unavailable"],
    }
    payload = collect_all(Session(), config, NOW)
    assert payload["total_items"] == 1
    assert [status["ok"] for status in payload["source_status"]] == [True, False, False]
    assert payload["source_status"][2]["skipped"] is True
    assert any("offline" in gap for gap in payload["info_gaps"])
    assert any("not stable" in gap for gap in payload["info_gaps"])


def test_youtube_transient_404_is_retried_and_still_reported_honestly():
    class Response:
        def __init__(self, status_code, content=b""):
            self.status_code = status_code
            self.content = content

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    recent = (NOW - timedelta(hours=1)).isoformat()
    xml = f'''<feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <title>Robot build</title><link href="https://www.youtube.com/watch?v=x"/>
      <published>{recent}</published></entry></feed>'''.encode()

    class Session:
        def __init__(self):
            self.calls = 0

        def get(self, *_args, **_kwargs):
            self.calls += 1
            return Response(404) if self.calls == 1 else Response(200, xml)

    session = Session()
    payload = collect_all(
        session,
        {
            "sources": [
                source(
                    "youtube_maker",
                    "youtube_rss",
                    name="YouTube · Maker",
                    url="https://www.youtube.com/feeds/videos.xml?channel_id=test",
                    allowed_hosts=["www.youtube.com"],
                    default_tags=["creative-video"],
                    window_hours=168,
                )
            ]
        },
        NOW,
    )
    assert session.calls == 2
    assert payload["source_status"][0]["ok"] is True
    assert payload["total_items"] == 1
