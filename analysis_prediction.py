"""Predictive analysis: does speech rhetoric add information about next-year conflict?

Toolbox for the predictive part (called by scripts/run_prediction.py and
predictive_analysis.ipynb). It reads the outputs of the earlier pipeline steps:

- outputs/prepared.parquet        (scripts/prepare_analysis.py)
- outputs/ucdp_country_year.parquet (scripts/prepare_analysis.py)
- outputs/rhetoric_full.sqlite    (scripts/score_speeches.py, shared cache)

Design (see RESEARCH_DESIGN.md and PREDICTION_RESULTS.md):
- Unit: country-year, speech years 1990-2024, main population only.
- Target: conflict_active_t1 (government-side UCDP conflict in year t+1).
- Models: persistence baseline and a ladder of L2 logistic regressions
  (history -> + spending -> + rhetoric), fixed C=1, no class reweighting.
- Validation: expanding window, trained through 2004/2008/2012/2016 and
  validated on the following four speech years each; final models trained
  through 2020 and evaluated once on 2021-2024.
- Metrics: average precision (primary) and ROC-AUC, on all rows and on rows
  that are at peace in year t (conflict onset).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from rhetoric_scoring import read_cache

ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Feature groups
# ---------------------------------------------------------------------------
HISTORY = ["conflict_active_t", "any_war_t", "n_conflicts_t", "conflict_years_past5"]
SPENDING = ["log_milex"]
RHETORIC = ["trust_score", "threat_score"]
CONTROLS = ["year", "log_words"]          # plus speaker_post_group (one-hot)
CATEGORICAL = ["speaker_post_group"]
TARGET = "conflict_active_t1"

VALIDATION_ROUNDS = [2004, 2008, 2012, 2016]   # last training year of each round
ROUND_LENGTH = 4                               # validation years per round
FINAL_TRAIN_END = 2020
FINAL_TEST_YEARS = (2021, 2024)


# ---------------------------------------------------------------------------
# 1. Modelling table
# ---------------------------------------------------------------------------
def load_inputs(root: Path = ROOT):
    """Load the three pipeline outputs the predictive analysis needs."""
    prepared = pd.read_parquet(root / "outputs/prepared.parquet")
    scores = read_cache(root / "outputs/rhetoric_full.sqlite")
    ucdp = pd.read_parquet(root / "outputs/ucdp_country_year.parquet")
    return prepared, scores, ucdp


def build_modelling_table(prepared: pd.DataFrame, scores: pd.DataFrame,
                          ucdp: pd.DataFrame) -> pd.DataFrame:
    """One row per main-population country-year 1990-2024 with a known t+1 outcome."""
    df = prepared.merge(
        scores[["entity_id", "year", "trust_score", "threat_score"]],
        on=["entity_id", "year"], how="left", validate="one_to_one",
    )
    if df["trust_score"].isna().any():
        raise ValueError("Some speeches have no rhetoric score")

    data = df[
        df["main_population"]
        & df["year"].between(1990, 2024)
        & df[TARGET].notna()
    ].copy()

    # Conflict history: number of UCDP conflict years in t-1 ... t-5.
    # The UCDP table only lists country-years with an active conflict.
    conflict_years = set(zip(ucdp["entity_id"], ucdp["year"]))
    data["conflict_years_past5"] = 0
    for k in range(1, 6):
        data["conflict_years_past5"] += [
            (country, year - k) in conflict_years
            for country, year in zip(data["entity_id"], data["year"])
        ]

    data["log_words"] = np.log(data["speech_token_count"])
    # log(1 + spending in percent of GDP); missing spending stays missing.
    data["log_milex"] = np.log1p(data["milex_share_gdp_t"] * 100)
    data[TARGET] = data[TARGET].astype(int)
    return data.reset_index(drop=True)


def model_comparisons(data: pd.DataFrame) -> dict:
    """The two model ladders, each evaluated on identical rows."""
    return {
        "all countries": (data, {
            "history": HISTORY + CONTROLS,
            "history + rhetoric": HISTORY + RHETORIC + CONTROLS,
        }),
        "countries with spending data": (data[data["milex_share_gdp_t"].notna()], {
            "history": HISTORY + CONTROLS,
            "history + spending": HISTORY + SPENDING + CONTROLS,
            "history + spending + rhetoric": HISTORY + SPENDING + RHETORIC + CONTROLS,
        }),
    }


# ---------------------------------------------------------------------------
# 2. Models
# ---------------------------------------------------------------------------
def fit_logit(numeric_features: list[str], train_data: pd.DataFrame,
              y_train: pd.Series):
    """Standardised numeric features + one-hot speaker post, L2 logistic regression (C=1).

    Scaling and encoding are learned from the training rows only.
    """
    prep = make_column_transformer(
        (StandardScaler(), numeric_features),
        (OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    )
    model = make_pipeline(prep, LogisticRegression(C=1.0, max_iter=1000))
    model.fit(train_data, y_train)
    return model


def _fit_and_predict(sample, model_specs, train_end, test_start, test_end):
    train = sample[sample["year"] <= train_end]
    test = sample[sample["year"].between(test_start, test_end)]
    y_train, y_test = train[TARGET], test[TARGET]
    predictions = {"persistence": test["conflict_active_t"].to_numpy()}
    fitted = {}
    for name, features in model_specs.items():
        fitted[name] = fit_logit(features, train, y_train)
        predictions[name] = fitted[name].predict_proba(test)[:, 1]
    return test, predictions, fitted


def _score_rows(sample_name, period, test, predictions):
    y = test[TARGET].to_numpy()
    peaceful = (test["conflict_active_t"] == 0).to_numpy()
    rows = []
    for name, prob in predictions.items():
        rows.append({
            "sample": sample_name,
            "test_years": period,
            "model": name,
            "n_rows": len(y),
            "n_conflicts": int(y.sum()),
            "n_onsets": int(y[peaceful].sum()),
            "AP_all": average_precision_score(y, prob),
            "ROC_AUC_all": roc_auc_score(y, prob),
            "AP_peaceful": average_precision_score(y[peaceful], prob[peaceful]),
            "onset_share_peaceful": y[peaceful].mean(),
        })
    return rows


# ---------------------------------------------------------------------------
# 3. Validation rounds and final evaluation
# ---------------------------------------------------------------------------
def run_validation_rounds(data: pd.DataFrame) -> pd.DataFrame:
    """Expanding-window validation: one row per sample x round x model."""
    rows = []
    for sample_name, (sample, specs) in model_comparisons(data).items():
        for train_end in VALIDATION_ROUNDS:
            start, end = train_end + 1, train_end + ROUND_LENGTH
            test, predictions, _ = _fit_and_predict(sample, specs, train_end, start, end)
            rows += _score_rows(sample_name, f"{start}-{end}", test, predictions)
    return pd.DataFrame(rows)


def run_final_evaluation(data: pd.DataFrame):
    """Train through 2020, evaluate once on 2021-2024. Returns (scores, fitted models)."""
    rows, models = [], {}
    start, end = FINAL_TEST_YEARS
    for sample_name, (sample, specs) in model_comparisons(data).items():
        test, predictions, fitted = _fit_and_predict(sample, specs, FINAL_TRAIN_END, start, end)
        rows += _score_rows(sample_name, f"{start}-{end}", test, predictions)
        for name, model in fitted.items():
            models[(sample_name, name)] = model
    return pd.DataFrame(rows), models


def summary_table(scores: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Models as rows, periods as columns, plus the mean across periods."""
    table = scores.pivot_table(index=["sample", "model"], columns="test_years",
                               values=metric, sort=False)
    table["mean"] = table.mean(axis=1)
    return table


def coefficient_table(models: dict) -> pd.DataFrame:
    """Standardised logistic-regression coefficients of the final models."""
    columns = {}
    for (sample_name, model_name), model in models.items():
        names = [n.split("__", 1)[1] for n in model[:-1].get_feature_names_out()]
        columns[f"{sample_name}: {model_name}"] = pd.Series(model[-1].coef_[0], index=names)
    table = pd.DataFrame(columns)
    main = HISTORY + SPENDING + RHETORIC + CONTROLS
    return table.loc[main + [i for i in table.index if i not in main]]


# ---------------------------------------------------------------------------
# 4. Figure
# ---------------------------------------------------------------------------
MODEL_COLORS = {"persistence": "#9a9a92", "history": "#2a78d6", "history + rhetoric": "#eb6834"}


def plot_rounds(rounds: pd.DataFrame, final: pd.DataFrame | None = None, path: Path | None = None):
    """Grouped bars: persistence vs history vs history + rhetoric, all countries.

    Left: all rows. Right: rows at peace in year t (onset prediction).
    If `final` is given, the held-out 2021-2024 period is added as a fifth group.
    """
    import matplotlib.pyplot as plt

    frames = [rounds]
    if final is not None:
        frames.append(final)
    plot_data = pd.concat(frames)
    plot_data = plot_data[plot_data["sample"] == "all countries"]
    order = list(MODEL_COLORS)
    periods = list(dict.fromkeys(plot_data["test_years"]))
    labels = [p + ("\n(held-out)" if final is not None and p == periods[-1] else "") for p in periods]
    x = np.arange(len(periods))
    width = 0.26

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    panels = [(axes[0], "AP_all", "All countries"),
              (axes[1], "AP_peaceful", "Only countries at peace in year t (onsets)")]
    for ax, metric, title in panels:
        for i, name in enumerate(order):
            values = (plot_data[plot_data["model"] == name]
                      .set_index("test_years").loc[periods, metric])
            ax.bar(x + (i - 1) * width, values, width - 0.02, label=name, color=MODEL_COLORS[name])
        if final is not None:
            ax.axvline(len(periods) - 1.5, color="#5f5f58", linewidth=0.8, linestyle="--")
        ax.set_xticks(x, labels)
        ax.set_xlabel("Evaluation period (speech years)")
        ax.set_ylabel("Average precision")
        ax.set_ylim(0, 1)
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    axes[1].legend(frameon=False, loc="upper left")
    fig.suptitle("Does rhetoric improve next-year conflict prediction beyond conflict history?")
    fig.text(0.01, 0.005,
             "Main-population country-years; each period uses models trained on all earlier speech years. "
             "Persistence = 'next year same as this year'.",
             fontsize=8, color="#5f5f58")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    if path is not None:
        fig.savefig(path, dpi=150)
    return fig
