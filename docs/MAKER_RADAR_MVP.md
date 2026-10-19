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
- `scripts/idea_bank.py`: local, explicit save/ignore/research actions.
- `scripts/build_maker_digest.py`: command-line entry point for producing a digest.
- `config/maker-radar.json`: the initial user profile and product limits.
- `tests/test_maker_opportunity.py` and `tests/test_idea_bank.py`: behavior contract.

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

## Next milestone

Feed existing public candidates from GitHub Trending, Product Hunt, RSS and
Hacker News into an opportunity-analysis stage. The analysis stage may use an
LLM when configured, but deterministic validation and selection must keep
working without a model key.
