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

Run the deterministic stage with normalized candidate data:

```bash
python scripts/build_maker_digest.py \
  --input data/maker-candidates.json \
  --output data/maker-daily.json \
  --idea-bank data/idea-bank.json \
  --info-gap "YouTube search unavailable"
```

## Next milestone

Feed existing public candidates from GitHub Trending, Product Hunt, RSS and
Hacker News into an opportunity-analysis stage. The analysis stage may use an
LLM when configured, but deterministic validation and selection must keep
working without a model key.
