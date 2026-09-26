# Full-speech transition-aware EDA

Reproduced 26 September 2026 using the verified whole-speech-v2 cache. This is a
descriptive analysis record, not final paper conclusions or predictive results.
No prompts, scoring rules, populations or models were selected based on these
comparisons. No new transformer inference was required.

## Population and transitions

Eligible main-population speech years 1990–2024 with observed current and exact
next-year government-side UCDP status: 6,445 country-years from 193 countries.
Requiring observed SIPRI leaves 5,071 country-years from 165 countries. Missing
spending is excluded, never set to zero. The full new scores recover 15 eligible
target rows absent from the old score cache; 11 of those also have SIPRI, explaining
the earlier audit's 6,430/5,060 counts versus 6,445/5,071 now.

| Transition | All scored rows | Countries | Rows with SIPRI | Countries with SIPRI |
| --- | ---: | ---: | ---: | ---: |
| Peace → peace | 5,224 | 185 | 3,979 | 155 |
| Peace → conflict | 159 | 72 | 140 | 68 |
| Conflict → conflict | 903 | 69 | 816 | 64 |
| Conflict → peace | 159 | 73 | 136 | 60 |

Countries can appear in multiple groups over time. These are country-year
transition occurrences, not counts of battles or unique UCDP conflicts.
Onset includes recurrence after a peace year. About 85% of next-year conflict
positives are continuation (903/1,062). Among currently peaceful rows, only
159/5,383 (3.0%) become conflict-positive next year.

## Identical-row descriptive summaries

All three variables below use the same SIPRI-complete row set in each group.
Theme scores are token-weighted means of passage compatibility, not calibrated
probabilities of trust, aggression, or conflict.

| Transition | Cooperation mean / median | Threat mean / median | Military spending mean / median (% GDP) |
| --- | ---: | ---: | ---: |
| Peace → peace | 0.342 / 0.331 | 0.099 / 0.046 | 1.927 / 1.473 |
| Peace → conflict | 0.302 / 0.275 | 0.113 / 0.061 | 2.447 / 1.620 |
| Conflict → conflict | 0.299 / 0.278 | 0.134 / 0.097 | 3.075 / 2.476 |
| Conflict → peace | 0.317 / 0.308 | 0.122 / 0.080 | 3.683 / 1.959 |

The groups overlap extensively. Means and medians can tell different stories:
cessation has the largest mean spending but not the largest median. Genuine
extreme values remain, including Kuwait 1991 above 100% of GDP. They are not
silently deleted, capped or mislabelled as impossible proportions.

## Uncertainty respecting repeated countries

Resample complete countries, retaining all their years, 2,000 times with seed
20260925. The following are pointwise 95% percentile intervals for differences
in group means, not causal effects or adjusted regression estimates.

| Contrast on identical SIPRI rows | Difference | 95% country-bootstrap interval |
| --- | ---: | ---: |
| Onset minus continued peace: cooperation | −0.0397 | [−0.0719, −0.0076] |
| Onset minus continued peace: threat | +0.0142 | [−0.0135, +0.0441] |
| Onset minus continued peace: spending | +0.519 percentage points | [−0.027, +1.227] |
| Continued conflict minus cessation: cooperation | −0.0173 | [−0.0576, +0.0217] |
| Continued conflict minus cessation: threat | +0.0126 | [−0.0145, +0.0387] |
| Continued conflict minus cessation: spending | −0.608 percentage points | [−2.736, +0.675] |

Cooperation's onset contrast also remains negative in the all-country comparison:
−0.0360, interval [−0.0671, −0.0056]. Threat's all-country onset interval still
includes zero: +0.0243, interval [−0.0020, +0.0524].

Interpretation: lower cooperation compatibility before onset is a **suggestive
descriptive association** under this measurement. The other prespecified
contrasts are less clear in these resampling intervals. An interval including
zero does not prove no relationship; it reflects uncertainty at this sample size.
An interval excluding zero does not show a useful prediction or causal mechanism.

These intervals are not adjusted for the multiple contrasts and populations.
They are exploratory, not a family-wise confirmatory significance test. Do not
promote one positive contrast while hiding the others. Sampling countries
addresses within-country repetition but not shared global shocks, changing
country composition, measurement error, confounding or publication timing.
The comparisons do not adjust for year, region or conflict history. Those
limitations remain for the planned predictive/robustness work.

## Passage review and measurement limits

Eighteen reproducibly sampled passages span three eras, seven regions and score
bands for both themes. See PASSAGE_REVIEW.md for all first-pass judgements and
subsequent score comparisons. This was an AI-assisted inspection with numeric
scores/outcomes withheld initially, not independent human annotation.

Some examples fit the intended broad themes. Others show important weaknesses:
high threat can represent disarmament or condemnation of foreign violence, while
substantive cooperation/conflict mentions can receive very low scores. Co-occurring
themes are sometimes poorly captured. Remaining OCR fragments and transcript
punctuation also warrant disclosure. The scores must not be renamed sentiment,
actual trust or military intent, and this small sample is not an accuracy study.

The model was not rescored or retuned in response. Human reviewers should rate
the blinded sample before looking at the AI judgements or model scores.

## Figures and reproducibility

Run from the project folder with Python 3.11:

```bash
python scripts/review_and_eda.py
```

This validates the cache, generates the same review sample, and recreates all
tables and figures in `outputs/whole_speech_eda/`. It does not download a model,
repeat scoring, or fit predictive models. Small aggregate tables and figures are shared in `results/`; speech-level data remain outside Git.
An independent repeat matched all eight generated CSV files byte-for-byte.
The sampler returns the same IDs. Existing human ratings in the blinded worksheet
are preserved on rerun; a different sample fails rather than overwriting them.
The original verification suite passed 60 tests before simplification. The suite
is retained in a local backup, not required to run this submission.

After simplification, the notebook executed from a fresh kernel. A command-line
rerun reproduced all six published tables and three figures byte-for-byte;
the completed score cache was unchanged.

Figures visually inspected:

- `score_ecdf_by_conflict_transition.png`: full distributions for both themes,
  all eligible target-observed rows, group sizes shown. A curve shows the
  proportion of speeches at or below each score; overlapping curves indicate
  overlapping distributions, not distinct classes.
- `military_spending_ecdf_by_conflict_transition.png`: SIPRI-complete sample,
  correct % GDP units, all observations retained. The horizontal scale is linear
  through 1% and logarithmic above, explicitly labelled, to show the bulk and tail.
- `whole_speech_score_trends_1990_2024.png`: unadjusted annual means with annual
  sample sizes. Differences across the two score levels are not comparisons of
  calibrated theme prevalence; composition and global agendas can change over time.

2025 is excluded from these substantive comparisons because it has no observed
next-year target and separate transcript-boundary issues. Its supplied text
remains in the prepared corpus; Session 81 is excluded as instructed.

## Next step

Obtain the short independent human passage review, then implement the planned
predictive comparison using chronological baselines. The question
is whether rhetoric improves held-out predictions beyond current conflict,
history and spending, not whether one descriptive interval excludes zero.
Final predictive results and final report conclusions have not been produced.
