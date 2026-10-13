# Which Model Am I?

A static questionnaire that estimates an AI agent's base model from dated facts and documented offline knowledge cutoffs.

## Run

```sh
uv sync
pnpm install
pnpm dev
```

Let the AI agent open the page and answer from memory. Each answer narrows a date interval; the result ranks matching models.

## Update

Follow [the compile skill](skills/compile-questionnaire/SKILL.md). The [cutoff catalog](data/model_cutoffs.parquet) and [versioned questionnaires](data/questionnaires/) are the source data. Run `pnpm build` before deployment.
