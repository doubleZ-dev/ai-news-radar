#!/usr/bin/env python3
"""Deterministic public-source adapters for Maker Inspiration Radar."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import html
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse, urlunparse

import feedparser
from bs4 import BeautifulSoup

from scripts.project_sources import parse_github_trending, source_timestamp


UTC = timezone.utc
MAKER_TERMS = {
    "3d-printing": ("3d print", "3d-print", "openscad", "filament", "slicer", "cad"),
    "embedded": ("esp32", "arduino", "raspberry pi", "microcontroller", "firmware", "sensor"),
    "robotics": ("robot", "servo", "stepper", "kinetic", "drone", "rover"),
    "fabrication": ("cnc", "laser cut", "pcb", "solder", "mechanical", "enclosure"),
    "interaction": ("e-ink", "eink", "display", "wearable", "haptic", "led", "desktop"),
    "open-source": ("open source", "open-source", "open hardware", "diy", "maker"),
}


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def clean_text(value: Any, limit: int = 1000) -> str:
    raw = str(value or "")
    text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True) if "<" in raw else html.unescape(raw)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def safe_public_url(value: Any, allowed_hosts: Iterable[str] | None = None) -> str:
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError:
        return ""
    hosts = {host.lower() for host in (allowed_hosts or [])}
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or (hosts and parsed.hostname.lower() not in hosts)
    ):
        return ""
    return urlunparse(("https", parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", parsed.query, ""))


def maker_tags(*values: Any) -> list[str]:
    blob = " ".join(str(value or "") for value in values).lower()
    def contains(term: str) -> bool:
        if term in {"3d print", "3d-print"}:
            return bool(re.search(r"(?<![a-z0-9])3d[- ]print(?:ed|er|ers|ing)?(?![a-z0-9])", blob))
        if term == "robot":
            return bool(re.search(r"(?<![a-z0-9])robot(?:s|ic|ics)?(?![a-z0-9])", blob))
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", blob))

    return [tag for tag, terms in MAKER_TERMS.items() if any(contains(term) for term in terms)]


def discovery_id(source_id: str, url: str) -> str:
    digest = hashlib.sha256(f"{source_id}\n{url}".encode("utf-8")).hexdigest()[:16]
    return f"discovery_{digest}"


def heat_from_count(
    label: str,
    count: int | None,
    thresholds: tuple[int, int, int, int, int] = (1, 5, 15, 40, 100),
) -> tuple[int | None, list[str]]:
    if count is None:
        return None, []
    score = sum(count >= threshold for threshold in thresholds)
    return score, [f"{label}: {count}"]


def make_record(
    *,
    source_id: str,
    source_name: str,
    category: str,
    title: str,
    url: str,
    summary: str,
    published_at: datetime | None,
    observed_at: datetime,
    tags: Iterable[str] = (),
    metrics: Mapping[str, Any] | None = None,
    heat_score: int | None = None,
    heat_evidence: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "discovery_id": discovery_id(source_id, url),
        "category": category,
        "source_id": source_id,
        "source": source_name,
        "title": title,
        "url": url,
        "published_at": iso(published_at),
        "observed_at": iso(observed_at),
        "summary": summary,
        "tags": sorted(set(tags)),
        "metrics": dict(metrics or {}),
        "heat_score": heat_score,
        "heat_evidence": list(heat_evidence),
        "analysis_state": "pending",
        "evidence_links": {"source": [url]},
    }


def parse_rss_source(xml: str, config: Mapping[str, Any], now: datetime) -> list[dict[str, Any]]:
    feed = feedparser.parse(xml)
    if not feed.entries:
        raise ValueError(f"{config['name']} returned no feed entries")
    cutoff = now - timedelta(hours=int(config.get("window_hours", 72)))
    allowed_hosts = config.get("allowed_hosts") or []
    records = []
    seen = set()
    for entry in feed.entries[:80]:
        title = clean_text(entry.get("title"), 240)
        url = safe_public_url(entry.get("link"), allowed_hosts)
        published = source_timestamp(entry.get("published") or entry.get("updated"))
        if not title or not url or url in seen or published is None or not cutoff <= published <= now:
            continue
        seen.add(url)
        summary = clean_text(entry.get("summary") or entry.get("description"))
        raw_comments = entry.get("slash_comments")
        try:
            comments = int(raw_comments) if raw_comments is not None else None
        except (TypeError, ValueError):
            comments = None
        heat, evidence = heat_from_count("comments", comments)
        records.append(
            make_record(
                source_id=str(config["id"]),
                source_name=str(config["name"]),
                category=str(config["category"]),
                title=title,
                url=url,
                summary=summary,
                published_at=published,
                observed_at=now,
                tags=maker_tags(title, summary),
                metrics={"comments": comments},
                heat_score=heat,
                heat_evidence=evidence,
            )
        )
    return records


def parse_github_source(html: str, config: Mapping[str, Any], now: datetime) -> list[dict[str, Any]]:
    records = []
    for project in parse_github_trending(html, now):
        tags = maker_tags(project["project_name"], project["summary"])
        if not tags:
            continue
        stars = project.get("stars_today")
        heat, evidence = heat_from_count(
            "stars today", stars, thresholds=(10, 50, 200, 500, 1000)
        )
        records.append(
            make_record(
                source_id=str(config["id"]),
                source_name=str(config["name"]),
                category=str(config["category"]),
                title=project["project_name"],
                url=project["url"],
                summary=project["summary"],
                published_at=None,
                observed_at=now,
                tags=tags,
                metrics={"stars_today": stars, "source_rank": project["source_rank"]},
                heat_score=heat,
                heat_evidence=evidence,
            )
        )
    return records


def parse_hn_payloads(
    payloads: Iterable[tuple[str, Mapping[str, Any]]],
    config: Mapping[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    cutoff = now - timedelta(hours=int(config.get("window_hours", 72)))
    records = []
    seen = set()
    for query, payload in payloads:
        for hit in payload.get("hits", []):
            if not isinstance(hit, Mapping):
                continue
            object_id = str(hit.get("objectID") or "").strip()
            title = clean_text(hit.get("title") or hit.get("story_title"), 240)
            published = source_timestamp(hit.get("created_at"))
            if not object_id or object_id in seen or not title or published is None or not cutoff <= published <= now:
                continue
            tags = maker_tags(title)
            if not tags:
                continue
            seen.add(object_id)
            source_url = safe_public_url(hit.get("url"))
            discussion_url = f"https://news.ycombinator.com/item?id={object_id}"
            url = source_url or discussion_url
            points = max(0, int(hit.get("points") or 0))
            comments = max(0, int(hit.get("num_comments") or 0))
            engagement = points + comments * 2
            heat, evidence = heat_from_count("HN engagement (points + 2×comments)", engagement)
            records.append(
                make_record(
                    source_id=str(config["id"]),
                    source_name=str(config["name"]),
                    category=str(config["category"]),
                    title=title,
                    url=url,
                    summary="",
                    published_at=published,
                    observed_at=now,
                    tags=tags,
                    metrics={
                        "points": points,
                        "comments": comments,
                        "query": query,
                        "discussion_url": discussion_url,
                    },
                    heat_score=heat,
                    heat_evidence=evidence,
                )
            )
            records[-1]["evidence_links"]["discussion"] = [discussion_url]
    return records
