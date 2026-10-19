#!/usr/bin/env python3
"""Collect the public, pre-analysis candidate pool for Maker Radar."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.maker_sources import (
    parse_github_source,
    parse_hn_payloads,
    parse_follow_builders_x,
    parse_huggingface_daily,
    parse_producthunt_source,
    parse_rss_source,
    parse_youtube_source,
)


UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "maker-sources.json"


def collect_source(
    session: requests.Session, config: Mapping[str, Any], now: datetime
) -> list[dict[str, Any]]:
    source_type = config["type"]
    if source_type in {
        "rss",
        "youtube_rss",
        "github_trending",
        "producthunt",
        "huggingface_daily",
        "follow_builders_x",
    }:
        response = session.get(str(config["url"]), timeout=30)
        # YouTube channel feeds occasionally return a transient 404 even for a
        # valid channel. Retry only this known public-feed case; a persistent
        # error still remains visible in source status.
        if source_type == "youtube_rss":
            for retry_index in range(2):
                if getattr(response, "status_code", None) != 404:
                    break
                time.sleep(0.8 * (retry_index + 1))
                response = session.get(str(config["url"]), timeout=30)
        response.raise_for_status()
        if source_type == "rss":
            # Let feedparser inspect the feed's own XML/HTTP encoding metadata.
            # requests.text may otherwise assume ISO-8859-1 and corrupt UTF-8
            # punctuation before the parser sees it.
            return parse_rss_source(response.content, config, now)
        if source_type == "youtube_rss":
            return parse_youtube_source(response.content, config, now)
        if source_type == "github_trending":
            return parse_github_source(response.content.decode("utf-8", errors="replace"), config, now)
        if source_type == "producthunt":
            return parse_producthunt_source(response.content, config, now)
        if source_type == "huggingface_daily":
            return parse_huggingface_daily(response.json(), config, now)
        return parse_follow_builders_x(response.json(), config, now)
    if source_type == "hn_algolia":
        cutoff = int((now.timestamp() - int(config.get("window_hours", 72)) * 3600))
        payloads = []
        for query in config.get("queries", []):
            response = session.get(
                str(config["url"]),
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff}",
                    "hitsPerPage": 30,
                },
                timeout=20,
            )
            response.raise_for_status()
            payloads.append((str(query), response.json()))
        return parse_hn_payloads(payloads, config, now)
    raise ValueError(f"unsupported maker source type: {source_type}")


def collect_all(
    session: requests.Session, config: Mapping[str, Any], now: datetime
) -> dict[str, Any]:
    items = []
    statuses = []
    for source in config.get("sources", []):
        if not source.get("enabled", True):
            statuses.append(
                {
                    "source_id": source["id"],
                    "source": source["name"],
                    "category": source["category"],
                    "ok": False,
                    "skipped": True,
                    "item_count": 0,
                    "window_hours": source.get("window_hours"),
                    "duration_ms": 0,
                    "error": source.get("disabled_reason") or "disabled",
                }
            )
            continue
        started = time.perf_counter()
        error = None
        records = []
        try:
            records = collect_source(session, source, now)
            items.extend(records)
        except Exception as exc:
            error = str(exc)
        statuses.append(
            {
                "source_id": source["id"],
                "source": source["name"],
                "category": source["category"],
                "ok": error is None,
                "skipped": False,
                "item_count": len(records),
                "window_hours": source.get("window_hours"),
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "error": error,
            }
        )
    items.sort(key=lambda item: (item.get("published_at") or item["observed_at"]), reverse=True)
    return {
        "schema_version": 1,
        "generated_at": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "stage": "pre_analysis",
        "total_items": len(items),
        "items": items,
        "source_status": statuses,
        "info_gaps": list(config.get("declared_gaps", []))
        + [f"{status['source']}: {status['error']}" for status in statuses if not status["ok"]],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "maker-candidates.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers.update({"User-Agent": "MakerInspirationRadar/0.1 (+https://github.com/doubleZ-dev/ai-news-radar)"})
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    payload = collect_all(session, config, datetime.now(UTC))
    write_json(args.output, payload)
    healthy = sum(1 for status in payload["source_status"] if status["ok"])
    skipped = sum(1 for status in payload["source_status"] if status.get("skipped"))
    failed = len(payload["source_status"]) - healthy - skipped
    print(
        f"Wrote: {args.output} ({payload['total_items']} items, "
        f"{healthy} healthy, {skipped} skipped, {failed} failed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
