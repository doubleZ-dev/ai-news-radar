#!/usr/bin/env python3
"""Render the curated and complete daily Maker Radar Markdown reports."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.maker_analysis import validate_analysis_packet
from scripts.maker_opportunity import build_daily_digest


def score_text(value: Any) -> str:
    return "未知" if value is None else f"{value}/5"


def _line_list(values: list[str]) -> str:
    return "；".join(values) if values else "无可靠数据"


def render_curated(digest: Mapping[str, Any], source_status: list[Mapping[str, Any]]) -> str:
    lines = [
        "# Maker Radar · 每日创客灵感",
        "",
        f"> 生成时间：{digest['generated_at']}",
        "",
    ]
    for index, item in enumerate(digest["items"], 1):
        lines.extend(
            [
                f"## {index}. [{item['title']}]({item['url']})",
                "",
                f"- 来源：{item['source']}｜发布时间：{item.get('published_at') or '来源未提供'}",
                f"- 核心内容：{item['core_summary']}",
                f"- 热度：{score_text(item['heat_score'])}｜{_line_list(item['heat_evidence'])}",
                f"- 创客匹配：{item['maker_fit_score']}/5｜{_line_list(item['maker_fit_evidence'])}",
                f"- 为什么适合你：{item['why_for_user']}",
                f"- 项目想法：{item['project_idea']}",
                f"- 最小验证：{'；'.join(item['minimum_validation']['steps'])}",
                f"- 成本／时间：{item['minimum_validation']['estimated_cost']}｜{item['minimum_validation']['estimated_time']}",
                f"- 难度：{item['difficulty']}",
                f"- 已核实事实：{_line_list(item['facts'])}",
                f"- AI 推测：{_line_list(item['agent_inferences'])}",
                f"- 风险：{_line_list(item['risks'])}",
                "- 操作：保存 / 忽略 / 候选研究",
                "",
            ]
        )
    by_id = {item["opportunity_id"]: item for item in digest["items"]}
    lines.extend(["## 今天最值得关注的 2 条", ""])
    for opportunity_id in digest["top_focus_ids"]:
        item = by_id[opportunity_id]
        lines.append(f"- [{item['title']}]({item['url']})：{item['why_for_user']}")
    lines.extend(["", "## 今天最值得加入 Idea Bank 的方向", ""])
    lines.extend(f"- {idea}" for idea in digest["idea_bank_directions"])
    lines.extend(["", "## 今天的信息缺口", ""])
    lines.extend(f"- {gap}" for gap in digest["info_gaps"])
    lines.extend(
        [
            "",
            "## 来源状态",
            "",
            "| 来源 | 状态 | 条数 |",
            "| --- | --- | ---: |",
        ]
    )
    for status in source_status:
        if status.get("ok"):
            state = "正常"
        elif status.get("skipped"):
            state = f"已跳过：{status.get('error')}"
        else:
            state = f"失败：{status.get('error')}"
        lines.append(f"| {status.get('source')} | {state} | {status.get('item_count', 0)} |")
    return "\n".join(lines).rstrip() + "\n"


def render_all_discoveries(
    raw_payload: Mapping[str, Any], analysis: Mapping[str, Any]
) -> str:
    decisions = {item["discovery_id"]: item for item in analysis["decisions"]}
    lines = [
        "# Maker Radar · 全部发现",
        "",
        f"> 采集时间：{raw_payload.get('generated_at')}｜共 {len(raw_payload['items'])} 条",
        "",
        "本页保留完整候选和原始链接；未进入精选不等于内容没有价值。",
        "",
    ]
    for index, item in enumerate(raw_payload["items"], 1):
        decision = decisions[item["discovery_id"]]
        label = "进入精选" if decision["selected"] else "未进入精选"
        metrics = "；".join(
            f"{key}={value}"
            for key, value in item.get("metrics", {}).items()
            if value is not None
        )
        lines.extend(
            [
                f"## {index}. [{item['title']}]({item['url']})",
                "",
                f"- 来源：{item['source']}｜发布时间：{item.get('published_at') or '来源未提供'}",
                f"- 原始摘要：{item.get('summary') or '来源未提供摘要'}",
                f"- 热度：{score_text(item.get('heat_score'))}｜{_line_list(item.get('heat_evidence') or [])}",
                f"- 原始指标：{metrics or '无可靠数据'}",
                f"- 标签：{', '.join(item.get('tags') or []) or '未标注'}",
                f"- 决策：{label}｜{decision['reason']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def report_output_dir(base: Path, report_date: str, dated_subdir: bool) -> Path:
    """Return the archive directory without relying on shell date expansion."""
    return base / report_date.replace("-", "") if dated_subdir else base


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--analysis", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--dated-subdir",
        action="store_true",
        help="create a YYYYMMDD folder below output-dir for Obsidian-style archives",
    )
    args = parser.parse_args()
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    analysis_raw = json.loads(args.analysis.read_text(encoding="utf-8"))
    analysis = validate_analysis_packet(raw, analysis_raw)
    digest = build_daily_digest(
        analysis["opportunities"],
        info_gaps=raw.get("info_gaps", []) + analysis.get("info_gaps", []),
    )
    report_date = datetime.fromisoformat(
        digest["generated_at"].replace("Z", "+00:00")
    ).date().isoformat()
    output_dir = report_output_dir(args.output_dir, report_date, args.dated_subdir)
    curated_path = output_dir / f"{report_date}-每日精选.md"
    all_path = output_dir / f"{report_date}-全部发现.md"
    write_text(curated_path, render_curated(digest, raw.get("source_status", [])))
    write_text(all_path, render_all_discoveries(raw, analysis))
    print(f"Wrote: {curated_path} ({digest['total_items']} selected)")
    print(f"Wrote: {all_path} ({raw['total_items']} discoveries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
