# Questionnaire data format

`data/model_cutoffs.csv` is the editable source catalog. The Parquet file has the same columns and is regenerated from CSV.

| Expression | Meaning |
| --- | --- |
| `=2025-01-01` | Exact date |
| `>2025-01-01&<2025-06-01` | Strict open interval |
| `>2025-01-01` | Strict lower bound |
| `<2025-06-01` | Strict upper bound |

`cutoff_basis` is `official_knowledge_cutoff`, `official_knowledge_cutoff_month`, `official_reliable_knowledge_cutoff`, or `release_date_upper_bound`. A release date only supplies an upper bound. `evidence_url` is required; `corroboration_url` is optional.

Version 2 `question_bank.json` has `version`, `asOf`, and `checkpoints`. Each checkpoint has a unique `id`, a `date`, and exactly three `questions`. The date must equal the middle event date of the three questions. The events must fit within 90 days, and adjacent checkpoints must be at least 30 days apart. Each question has a unique `id`, `eventDate`, `category` (`society` or `technology`), Chinese `prompt`, four unique `{id,label}` `options`, `correctOptionId`, `unknownOptionId` equal to `unknown`, `sourcePublishedDate`, and `sourceUrl`. The cited source must be published from the event date through seven days later. At least two questions per checkpoint must have category `society`. The unknown option's label is `不知道／不确定`.

The compiled version 2 `questionnaire.json` and `current.json` have `schemaVersion`, `version`, `asOf`, `catalogSize`, `questionCount`, `root`, and a `nodes` map. A checkpoint node has its three questions, `threshold: 2`, and `next.correct` / `next.incorrect` node IDs. The engine displays one question at a time. At least two correct answers advance to the later interval. All other answer patterns advance to the earlier interval. A result node has an inclusive date `range`, `candidateCount`, and ranked `candidates` with model ID, provider, cutoff expression, basis, evidence URL, and heuristic fit. `null` range endpoints mean unbounded.

The compiler bisects sorted checkpoint dates recursively. Every checkpoint is reachable and each leaf corresponds to one interval between checkpoint dates. `check_questionnaire.py` verifies the compiled tree against the source bank and catalog, including continuous ranges and candidate ranking. It cannot decide whether a distractor is plausible or a question is common knowledge; these require manual review. Candidate fit is a sorting heuristic, not a probability. Version 1 files remain as historical artifacts; new questionnaires use version 2.
