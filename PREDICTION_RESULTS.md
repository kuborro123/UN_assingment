# Predictive analysis: rhetoric and next-year conflict

First complete version, 27 September 2026 (Gereon). This record describes what was run and
found. It is not the final report text. Code: `analysis_prediction.py`,
`scripts/run_prediction.py`, `predictive_analysis.ipynb`. Tables and figure:
[results/prediction/](results/prediction/).

## Question

Do speech-derived theme scores (trust/cooperation and military threat) improve
out-of-sample prediction of next-year government-side armed conflict beyond current
conflict, recent conflict history and military spending? Does any added value extend to
countries that are currently at peace (conflict onset)?

The EDA ([EDA_RESULTS.md](EDA_RESULTS.md)) motivates this question. Conflict is highly
persistent, and cooperation language is somewhat lower before onset, so the relevant test is
whether rhetoric adds information once conflict history is known.

## Data and setup

- **Rows:** 6,445 main-population country-years (193 countries), speech years 1990–2024,
  with an observed outcome in t+1. Of these, 5,071 rows (165 countries) have observed SIPRI
  spending. 16.5% of rows have conflict in t+1.
- **Target:** `conflict_active_t1`.
- **Features:** conflict now (`conflict_active_t`, `any_war_t`, `n_conflicts_t`). Conflict
  history: `conflict_years_past5`, the number of UCDP conflict years in t−5 … t−1, built from
  `outputs/ucdp_country_year.parquet`. Spending: `log(1 + % of GDP)`. Rhetoric:
  full-speech `trust_score` and `threat_score`. Controls: linear `year`, `log` speech length,
  and the speaker-post group (one-hot).
- **Models:** a persistence baseline (predicted next-year status = current status) and L2
  logistic regressions with standardised features, fixed `C = 1` and no class reweighting.
  Scaling and encoding are fitted on training rows only.
- **Comparisons on identical rows:**
  - All countries: history vs history + rhetoric.
  - Countries with spending data: history → + spending → + spending + rhetoric.
- **Validation:** expanding window. Models are trained through 2004, 2008, 2012 and 2016, and
  each is validated on the next four speech years. Final models are trained through 2020 and
  evaluated once on 2021–2024. Those years were not used for fitting or model choice, but
  they were visible in the team's EDA.
- **Metrics:** average precision (AP, primary) and ROC-AUC. AP for a model with no
  information equals the share of positives. Each model is graded on all rows and, separately,
  on rows at peace in year t (onset prediction).

## Results

### Validation periods: average precision, all rows

| Model (all countries) | 2005–08 | 2009–12 | 2013–16 | 2017–20 | Mean |
|---|---:|---:|---:|---:|---:|
| Persistence | 0.748 | 0.735 | 0.756 | 0.794 | 0.758 |
| History | 0.896 | 0.878 | 0.893 | 0.923 | 0.897 |
| History + rhetoric | 0.897 | 0.880 | 0.890 | 0.922 | 0.897 |

With spending data, history, + spending and + spending + rhetoric all average 0.896–0.897.

### Validation periods: average precision, onsets only (rows at peace in year t)

| Model (all countries) | 2005–08 | 2009–12 | 2013–16 | 2017–20 | Mean |
|---|---:|---:|---:|---:|---:|
| Persistence (= onset share) | 0.026 | 0.024 | 0.036 | 0.027 | 0.029 |
| History | 0.222 | 0.075 | 0.341 | 0.364 | 0.251 |
| History + rhetoric | 0.235 | 0.085 | 0.322 | 0.340 | 0.246 |

Each period contains only 16–23 onsets.

### Held-out evaluation, 2021–2024 (759 rows, 137 conflicts, 12 onsets)

| Sample | Model | AP all | ROC-AUC all | AP onsets |
|---|---|---:|---:|---:|
| All countries | Persistence | 0.867 | 0.949 | 0.019 |
| | History | 0.949 | 0.968 | 0.213 |
| | History + rhetoric | 0.950 | 0.969 | 0.228 |
| With spending | Persistence | 0.858 | 0.943 | 0.025 |
| | History | 0.944 | 0.963 | 0.183 |
| | History + spending | 0.945 | 0.964 | 0.225 |
| | History + spending + rhetoric | 0.945 | 0.965 | 0.234 |

### Final-model coefficients (odds ratio per one standard deviation)

| Feature | All countries: history + rhetoric | With spending: history + spending + rhetoric |
|---|---:|---:|
| Conflict years in past 5 | 2.52 | 2.68 |
| Conflict in year t | 2.28 | 2.30 |
| Number of conflicts in t | 1.85 | 1.99 |
| War in year t | 1.26 | 1.23 |
| log military spending | – | 1.05 |
| **Trust/cooperation score** | **0.87** | **0.84** |
| **Threat score** | **1.12** | **1.07** |
| Year | 1.19 | 1.20 |
| log speech length | 1.09 | 1.05 |

Full coefficient tables, including the speaker-post dummies, are in
`results/prediction/final_coefficients.csv` and `final_odds_ratios.csv`.

## Interpretation

1. **Conflict history is the dominant predictor.** It beats persistence in every period
   (mean AP 0.90 vs 0.76; held-out 0.95 vs 0.87), mainly by identifying recently peaceful
   countries that relapse and long wars that continue.
2. **Rhetoric does not reliably improve prediction.** Overall, the change in AP is at most
   ±0.003 in any period. For onsets, it is positive in three of five periods and negative in
   two, and each period has only 12–23 onsets. The held-out onset gain (+0.015) is within this
   variation. Military spending behaves the same way.
3. **Associations have the hypothesised direction but are small.** More cooperation
   language goes with lower odds of conflict and more threat language with higher odds. Per
   standard deviation, these effects are several times smaller than the history effects, and
   they barely change the ranking of countries that AP evaluates.
4. **Answer:** once conflict history is known, what countries say in the General Debate
   adds little usable information about next-year conflict, including for new onsets. This
   null result is a valid answer, and the report should present it as such.

## Limitations and deviations from RESEARCH_DESIGN.md

- **No uncertainty intervals for AP differences yet.** The design specifies paired
  country-bootstrap intervals. Without them, "no reliable gain" rests on consistency across
  periods, not on a formal interval.
- **Not yet implemented:** an "observed-history years" feature and explicit identity
  boundaries (for example, years before South Sudan existed count as no conflict in its
  history); Brier score, calibration plot, and a validation-chosen classification threshold;
  the region sensitivity analysis; onset/continuation strata as separate tables.
- **Few onsets** (12–23 per period) make onset metrics unstable.
- **The coefficients are regularised** (C = 1) and describe associations, not causal
  effects or significance. The rhetoric scores measure theme compatibility, not actual trust
  or intent (see EDA_RESULTS.md).
- **This is retrospective annual prediction:** annual conflict and spending data are
  published after the September speech. It is not a real-time early-warning system.

## Possible next steps

1. Country-bootstrap intervals for the AP difference (history + rhetoric minus history).
2. Brier score and calibration plot for the final models.
3. Onset-only models or an interaction between rhetoric and peace in year t, if the team
   wants to probe onsets further. These would be exploratory and should be labelled as such.

## Reproduce

```bash
python scripts/run_prediction.py
```

Or run `predictive_analysis.ipynb` from top to bottom. Both need the outputs of
`scripts/prepare_analysis.py` and the shared `outputs/rhetoric_full.sqlite`. Runtime is
under a minute, and no transformer inference is repeated.

Code preparation used AI assistance. Team members should review the methods and follow
the course's disclosure rules.
