# Maker Inspiration Radar MVP

This fork adds a maker-opportunity layer without destabilizing the upstream AI
news collector.

## First milestone

The first milestone freezes five product contracts before adding more sources:

1. Heat (`0..5` or unknown) and maker fit (`0..5`) remain independent.
2. Every known heat score carries verifiable evidence.
3. Daily selection is capped at eight and led by maker fit.
4. Previously recorded ideas stay suppressed unless an explicit substantial
   update is present.
5. A high score never promotes an idea into an active project.

The implementation lives in:

- `scripts/maker_opportunity.py`: validation, URL dedupe, selection, digest JSON.
- `scripts/maker_analysis.py`: auditable handoff from every raw discovery to a
  selected or rejected decision.
- `scripts/render_maker_reports.py`: UTF-8 curated and complete Markdown views.
- `scripts/idea_bank.py`: local, explicit save/ignore/research actions.
- `scripts/build_maker_digest.py`: command-line entry point for producing a digest.
- `prompts/maker-opportunity-analysis.md`: model instructions and JSON contract.
- `config/maker-radar.json`: the initial user profile and product limits.
- `docs/MAKER_SOURCE_STATUS.md`: live-validated source coverage and explicit skips.
- `tests/test_maker_analysis.py`, `tests/test_maker_opportunity.py`, and
  `tests/test_idea_bank.py`: behavior contract.

The local Idea Bank is intentionally ignored by Git. It may contain personal
preferences and must not be published through GitHub Pages by default.

Run the deterministic selection stage after the analysis stage has produced
fully normalized opportunity data (the pre-analysis candidate pool is not yet
valid input for this command):

```bash
python scripts/build_maker_digest.py \
  --input data/maker-opportunities.json \
  --output data/maker-daily.json \
  --idea-bank data/idea-bank.json \
  --info-gap "YouTube search unavailable"
```

Collect the public pre-analysis candidate pool first:

```bash
python scripts/collect_maker_candidates.py \
  --output data/maker-candidates.json
```

The source registry is `config/maker-sources.json`. Source failures and
platforms without a stable integration are preserved in `info_gaps`; an empty
or failed source is never reported as successfully scanned.

After an agent follows `prompts/maker-opportunity-analysis.md` and writes
`data/maker-analysis.json`, validate the traceability rules and render both
reader views:

```bash
python scripts/render_maker_reports.py \
  --raw data/maker-candidates.json \
  --analysis data/maker-analysis.json \
  --output-dir reports/daily
```

For an Obsidian archive, pass the vault folder and `--dated-subdir`. The
renderer then creates a `YYYYMMDD` directory automatically without overwriting
older dates.

The curated report contains five to eight opportunities. The complete report
retains every raw source link plus its explicit selection decision. Both are
local generated artifacts and are ignored by Git by default.

## Next milestone

YouTube channel Atom, Reddit, arXiv Robotics RSS, and Hackster Atom are now
integrated and live-validated. Stable maker/vendor feeds also cover Make,
Prusa, Bambu Lab, CNX Software, and Seeed Studio.

The remaining source work is MakerWorld, Printables, Bilibili, Kickstarter,
Crowd Supply, Instructables, Thingiverse, TikTok, WeChat, Douyin, and
Xiaohongshu. Prefer public feeds and APIs, preserve per-source failure
reporting, and avoid requiring a model API key in GitHub. Credentialed social
platforms stay optional until a private authorization path is configured.

Social sources follow the same rule: public curated snapshots may be enabled
after repeated validation, while account-bound or credentialed platforms stay
explicitly skipped until local authorization is configured.
