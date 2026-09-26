# UN speeches and conflict transitions

A university data-science project combining UN General Debate speeches,
UCDP/PRIO conflict data and SIPRI military spending (SDG 16).

**Completed:** data preparation, full-speech theme scoring and transition-aware
exploratory analysis. **Next:** independent passage review and predictive analysis.
The earlier team notebook is preserved in Git at commit `f44ce6f3`.

## Read the results

Open [main.ipynb](main.ipynb) for the workflow and [EDA_RESULTS.md](EDA_RESULTS.md)
for findings and limitations. Small reproduced tables and figures are in
[results/](results/). [RESEARCH_DESIGN.md](RESEARCH_DESIGN.md) describes the planned
predictive comparison. No predictive results or final paper conclusions exist yet.

## Setup

Use Python 3.11. From the project folder:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` to point to your local speech directory, speaker metadata, UCDP CSV
and SIPRI workbook. Leave `output_path=outputs`. Source versions are recorded in
[data-manifest.md](data-manifest.md). Country mappings are in [config/](config/).
Do not commit raw data or your machine-specific `.env`.

Obtain the completed **rhetoric_full.sqlite** from the teammate who ran scoring
and place it in `outputs/` (create that folder if needed). This file contains all
6,712 speech scores and their passage scores. The CSV export alone is insufficient
for passage review. Do not use the older prefix-score cache.

SHA-256 of the completed SQLite cache:
`4ab510d408644858d14c88338ce26d6cc7f669e0485452a047912ef7491c32d6`.

## Reproduce in two commands

```bash
python scripts/prepare_analysis.py
python scripts/review_and_eda.py
```

Alternatively, run `main.ipynb` from top to bottom using this environment.
The first step cleans and merges data; the second uses cached scores to produce
tables, figures and the blinded review worksheet under `outputs/whole_speech_eda/`.
These commands do not download the transformer or repeat inference.
The copies in `results/` are a published snapshot, not inputs to the analysis.

Expected: 6,712 prepared speeches, 6,633 in the main population, and 6,445
country-years with next-year targets. Of those, 5,071 have observed spending.
An unavailable or incompatible score cache produces an error rather than
silently using the old scores.

## Generate scores only if the cache is unavailable

```bash
pip install -r requirements-model.txt
python scripts/score_speeches.py --device auto --batch-size 8
```

This took about ten hours on the original Mac. It resumes compatible completed
batches after interruption. Do not run two scoring processes on the same cache.
Changing hardware or settings requires a separate cache via `--cache`.

The model and revision are pinned in `rhetoric_scoring.py`. It scores coherent
text in non-overlapping chunks of up to 480 tokens, evaluates cooperation and
military-threat labels independently, and averages by chunk length.
These are theme-compatibility scores, not sentiment or aggressive intent.

## Where the code lives

- `analysis_pipeline.py`: source loading, country reconciliation, text cleaning and joins.
- `text_dictionaries.py`: transparent diagnostic keyword features, not the final scores.
- `rhetoric_scoring.py`: transformer chunking, scoring and cache reading.
- `analysis_eda.py`: transition summaries, country-bootstrap intervals and figures.
- `scripts/`: three entry points for preparation, scoring and review/EDA.

The separate historical audit framework, automated test suite and unfinished
prediction code are not part of this streamlined submission. Only lightweight
input, join and cache-consistency checks remain in the runnable pipeline.

## Interpretation and next work

Speech years 1990–2024 have exact next-year conflict outcomes. 2025 remains in
the source table but not these comparisons; Session 81 is excluded. Missing
military spending is not zero. UCDP describes government-side conflict involvement,
not necessarily where fighting occurs. Annual data make this retrospective
analysis, not a real-time September forecast.

Ask one or two teammates to independently rate
`outputs/whole_speech_eda/passage_review_blinded.csv` before reading the model
key or [PASSAGE_REVIEW.md](PASSAGE_REVIEW.md). Then implement the chronological
predictive comparison in the research design. Do not claim predictive value
from descriptive group differences alone.

Code preparation and the initial passage review used AI assistance. Team members
should understand and review the methods and follow the course's disclosure rules.
