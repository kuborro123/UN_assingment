# Approved analysis specification

Frozen 25 September 2026, after the independent EDA audit and before new
whole-speech scores or predictive results. Student approval is recorded in the
conversation. This is not a claim of TA approval or preregistration before EDA.
Session 81 is excluded at the student's explicit instruction. Sessions 1–80
remain the source corpus. SDG 16 is the sole SDG used in the analysis.

## Questions and hypotheses

Exploratory: How do cooperation/trust-themed language, military-threat-themed
language and military burden differ across transitions between peace and
government-side state-based armed conflict?

Predictive: Do speech-derived theme scores add out-of-sample information about
next-year government-side conflict activity beyond current conflict, recent
conflict history and military burden, and does added value extend to currently
peaceful countries?

Directional hypotheses: threat-themed language and military burden are higher,
and cooperation/trust-themed language lower, before next-year conflict. Text may
improve prediction beyond conflict persistence, but this must be tested rather
than assumed. Strategic appeals for cooperation during conflict can reverse the
first hypothesis. Null or contrary findings remain valid answers.

The theme "Restoring trust, managing transformation" motivates studying public
diplomatic framing around conflict transitions. Topic compatibility is not actual
trust, intent, sentiment, or a causal influence on conflict. Government-side
UCDP location is not necessarily the battlefield or all secondary participants.

## Population and timing

One canonical entity-year speech, 1990–2025; supervised speech years 1990–2024.
Current UN member-state identities form the main population, with explicit
historical-state exclusions. This is not a historical membership-date roster.
EU, Holy See and Palestine remain in the prepared text table but not the main
model. Palestine's outcome cannot be constructed by assuming an absent UCDP
location is peace; any observer sensitivity requires a separate outcome review.
Use observed SIPRI values in the main sample and a no-SIPRI all-country
sensitivity. Never replace missing spending with zero.

The analysis is retrospective annual prediction, not a September early-warning
system: annual conflict/spending values include information after the speech and
are published/revised later. Outcomes join UCDP at exactly t+1 independently of
whether a speech exists in that year. Five-year history uses UCDP years t−5 to
t−1, not the previous five available speeches; identity coverage is explicit.
The historical identity boundaries will need to be implemented explicitly when
constructing predictive history features; pre-identity years must not be treated
as observed peace. Prediction has not yet been implemented in this submission.

## Fixed whole-speech measurement

Model: MoritzLaurer/ModernBERT-large-zeroshot-v2.0, revision
`a51e07b524299e309dd2b88d48b0cfa2bd9ec598`. Float32 inference, evaluation mode,
seed 20260925, no training. Device and package versions are recorded. Preserve
case, punctuation and negation; normalize Unicode/whitespace, preserve raw text,
and remove only identified chair boilerplate with removal flags. No stopwords,
stemming, country-name masking or outcome-informed vocabulary fitting.

Retain the team's labels `trust and international cooperation` and
`military threat and security concerns` with `This example is {}.`. Evaluate
independently as entailment versus not-entailment, not competing categories.
Partition the complete cleaned token sequence into non-overlapping chunks of at
most 480 model tokens. Prefer sentence-ending boundaries in the latter half of
each window; split overlong sentences at the token limit. Score every token
exactly once, with no silent truncation. Compute each speech score as the
token-count-weighted mean of chunk scores. Store the chunk count, complete token
count, coverage, text hash, per-chunk scores, and scoring specification hash.
The score describes average local theme compatibility, not whole-document
entailment. Splitting loses cross-chunk context; this is a disclosed limitation.

This repairs the silent prefix limitation while respecting the checkpoint's
512-token setting. Labels/template are retained to limit method search, not
because their p-values were favorable. The earlier switch from dictionaries
after weak results is exploratory and must be disclosed. Transparent dictionaries
are diagnostic comparisons, not replacement models selected for significance.
A reproducible stratified passage review checks construct plausibility before
predictive interpretation. Automated/AI review is not independent human validation.

## Predictive comparison (only after measurement checks)

Compare training prevalence, fixed current-conflict persistence, L2 logistic
history-only, history plus military burden, and history/spending plus the two
theme scores. History predictors: current activity, war indicator, number of
active conflicts, prior-five-year conflict count and observed-history years.
Prespecified nuisance controls in fitted models: linear year, log word count,
speaker-post group. Add region only as a labelled sensitivity, using a fixed
documented geographic classification, not current income as historical income.

Use fixed C=1, no class reweighting (retain probability interpretation), training
fold standardization and one-hot encoding with unknown categories ignored.
No model/prompt search for a positive result. Spending is transformed as
log(1 + percentage points) to reduce leverage of extreme positive values while
retaining genuine zeroes; retain raw units for EDA. All compared models use
identical evaluation rows. The all-country comparison omits spending throughout.

Expanding training through 2004, 2008, 2012 and 2016, each followed by four speech
years of validation. Train the final model through 2020 and evaluate speech
2021–2024 once after freeze. These final years were already seen in team EDA:
held out from model fitting/tuning is honest; wholly untouched is not.

Primary discrimination metric: average precision (stepwise PR-AUC convention).
Also Brier score, calibration plots, ROC-AUC, precision and recall. Choose a
classification threshold from chronological validation predictions to maximize
balanced accuracy (mean sensitivity and specificity), then lock it for final
evaluation. Persistence uses its fixed binary rule. Report onset/continuation
strata as secondary, noting sparse onsets. Paired country bootstrap intervals
for metric differences preserve country histories; fixed-model intervals do not
include model-refitting uncertainty or shared global shocks.

## Reporting gate

No final report conclusions until source reconstruction, score coverage/cache
checks, and statistical reproductions pass. Keep unsuccessful exploratory methods
and null gains visible. Distinguish descriptive separation, construct validity
and held-out predictive usefulness. A good grade is supported by transparent,
defensible reasoning, not by obtaining significant results.
