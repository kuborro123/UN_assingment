"""Transition-aware descriptive analysis for completed whole-speech scores.

This module is deliberately separate from score generation and predictive
modelling.  It accepts the validated, prepared entity-year table after the two
whole-speech scores have been attached.  It never chooses labels, prompts,
features, or populations using outcome separation.

The substantive EDA population is the frozen main population, speech years
1990--2024, with an observed UCDP outcome for year t+1.  Session 80 / 2025 is
therefore excluded from every substantive trend and transition comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rhetoric_scoring import SPEC_HASH


FEATURES = {
    "trust_score": {
        "label": "Trust/cooperation theme compatibility",
        "unit": "score in [0, 1]",
    },
    "threat_score": {
        "label": "Military-threat/security theme compatibility",
        "unit": "score in [0, 1]",
    },
    "milex_share_gdp_t": {
        "label": "Military expenditure share of GDP",
        "unit": "proportion (0.03 = 3% of GDP)",
    },
}

TRANSITIONS = {
    (0, 0): ("continued_peace", "Continued peace (0→0)"),
    (0, 1): ("onset", "Conflict onset (0→1)"),
    (1, 0): ("cessation", "Conflict cessation (1→0)"),
    (1, 1): ("continued_conflict", "Continued conflict (1→1)"),
}
TRANSITION_ORDER = [value[0] for value in TRANSITIONS.values()]
TRANSITION_LABEL = {value[0]: value[1] for value in TRANSITIONS.values()}
TRANSITION_COLOURS = {
    "continued_peace": "#4C78A8",
    "onset": "#E45756",
    "cessation": "#72B7B2",
    "continued_conflict": "#B279A2",
}

COMPARISONS = (
    ("onset_minus_continued_peace", "continued_peace", "onset"),
    ("continued_conflict_minus_cessation", "cessation", "continued_conflict"),
)


@dataclass(frozen=True)
class EDAArtifacts:
    """Files and in-memory tables created by :func:`generate_full_score_eda`."""

    output_dir: Path
    tables: dict[str, pd.DataFrame]
    figures: tuple[Path, ...]
    manifest_path: Path


def _validate_input(frame):
    """Basic checks before comparing the same country-year observations."""
    if frame.duplicated(["entity_id", "year"]).any():
        raise ValueError("Duplicate country-year rows")
    scores = frame[["trust_score", "threat_score"]]
    if scores.isna().any().any() or not scores.ge(0).all().all() or not scores.le(1).all().all():
        raise ValueError("Complete scores between zero and one are required")
    if frame.loc[frame.milex_status_t.ne("observed"), "milex_share_gdp_t"].notna().any():
        raise ValueError("Unavailable military spending must remain missing")


def _analysis_population(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    main_period = frame["main_population"].astype(bool) & frame["year"].between(1990, 2024)
    target_observed = frame["conflict_active_t1"].isin([0, 1])
    current_observed = frame["conflict_active_t"].isin([0, 1])
    selected = frame.loc[main_period & target_observed & current_observed].copy()
    if selected.empty:
        raise ValueError("No main-population 1990--2024 rows have observed t and t+1 conflict status")

    selected["conflict_active_t"] = selected["conflict_active_t"].astype(int)
    selected["conflict_active_t1"] = selected["conflict_active_t1"].astype(int)
    keys = list(zip(selected["conflict_active_t"], selected["conflict_active_t1"]))
    selected["transition"] = [TRANSITIONS[key][0] for key in keys]
    selected["transition_label"] = selected["transition"].map(TRANSITION_LABEL)
    selected["transition"] = pd.Categorical(
        selected["transition"], categories=TRANSITION_ORDER, ordered=True
    )

    audit = pd.DataFrame(
        [
            {
                "population_step": "input rows",
                "n_rows": len(frame),
                "n_countries": frame["entity_id"].nunique(),
            },
            {
                "population_step": "main population, 1990-2024",
                "n_rows": int(main_period.sum()),
                "n_countries": frame.loc[main_period, "entity_id"].nunique(),
            },
            {
                "population_step": "main 1990-2024 with observed t and t+1 status",
                "n_rows": len(selected),
                "n_countries": selected["entity_id"].nunique(),
            },
            {
                "population_step": "identical observed-SIPRI rows",
                "n_rows": int(selected["milex_status_t"].eq("observed").sum()),
                "n_countries": selected.loc[
                    selected["milex_status_t"].eq("observed"), "entity_id"
                ].nunique(),
            },
        ]
    )
    return selected, audit


def _sample_frames(population: pd.DataFrame) -> dict[str, pd.DataFrame]:
    complete = population.loc[
        population[[*FEATURES]].notna().all(axis=1)
        & population["milex_status_t"].eq("observed")
    ].copy()
    return {
        "all_target_observed": population,
        "sipri_complete_identical": complete,
    }


def transition_counts(population: pd.DataFrame) -> pd.DataFrame:
    """Count rows and countries for the full and SIPRI-identical samples."""
    records: list[dict[str, object]] = []
    for sample_name, sample in _sample_frames(population).items():
        denominator = len(sample)
        for transition in TRANSITION_ORDER:
            group = sample.loc[sample["transition"].eq(transition)]
            records.append(
                {
                    "sample": sample_name,
                    "transition": transition,
                    "transition_label": TRANSITION_LABEL[transition],
                    "n_rows": len(group),
                    "n_countries": group["entity_id"].nunique(),
                    "sample_rows": denominator,
                    "row_share": len(group) / denominator if denominator else np.nan,
                }
            )
    return pd.DataFrame(records)


def feature_summaries(population: pd.DataFrame) -> pd.DataFrame:
    """Summarise all available values and an identical SIPRI-complete sample."""
    records: list[dict[str, object]] = []
    samples = {
        "all_available_per_feature": population,
        "sipri_complete_identical": _sample_frames(population)["sipri_complete_identical"],
    }
    for sample_name, sample in samples.items():
        for transition in TRANSITION_ORDER:
            group = sample.loc[sample["transition"].eq(transition)]
            for feature, metadata in FEATURES.items():
                observed = group.dropna(subset=[feature])
                values = observed[feature].astype(float)
                q25 = values.quantile(0.25) if len(values) else np.nan
                q75 = values.quantile(0.75) if len(values) else np.nan
                records.append(
                    {
                        "sample": sample_name,
                        "transition": transition,
                        "transition_label": TRANSITION_LABEL[transition],
                        "feature": feature,
                        "feature_label": metadata["label"],
                        "unit": metadata["unit"],
                        "n_rows": len(values),
                        "n_countries": observed["entity_id"].nunique(),
                        "mean": values.mean() if len(values) else np.nan,
                        "median": values.median() if len(values) else np.nan,
                        "q25": q25,
                        "q75": q75,
                        "iqr": q75 - q25 if len(values) else np.nan,
                    }
                )
    return pd.DataFrame(records)


def _country_bootstrap_weights(
    countries: np.ndarray, n_bootstrap: int, random_seed: int
) -> np.ndarray:
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be at least one")
    rng = np.random.default_rng(random_seed)
    probabilities = np.repeat(1.0 / len(countries), len(countries))
    return rng.multinomial(len(countries), probabilities, size=n_bootstrap)


def _bootstrap_contrast(
    sample: pd.DataFrame,
    feature: str,
    reference: str,
    contrast: str,
    countries: np.ndarray,
    weights: np.ndarray,
) -> dict[str, object]:
    subset = sample.loc[
        sample["transition"].isin([reference, contrast]) & sample[feature].notna(),
        ["entity_id", "transition", feature],
    ].copy()
    grouped = (
        subset.groupby(["entity_id", "transition"], observed=True)[feature]
        .agg(["sum", "count"])
        .reindex(
            pd.MultiIndex.from_product(
                [countries, [reference, contrast]], names=["entity_id", "transition"]
            ),
            fill_value=0,
        )
    )
    sums = grouped["sum"].to_numpy(dtype=float).reshape(len(countries), 2)
    counts = grouped["count"].to_numpy(dtype=float).reshape(len(countries), 2)
    weighted_sums = weights @ sums
    weighted_counts = weights @ counts
    valid = (weighted_counts[:, 0] > 0) & (weighted_counts[:, 1] > 0)
    differences = (
        weighted_sums[valid, 1] / weighted_counts[valid, 1]
        - weighted_sums[valid, 0] / weighted_counts[valid, 0]
    )

    by_group = {}
    for transition in (reference, contrast):
        group = subset.loc[subset["transition"].eq(transition)]
        by_group[transition] = {
            "rows": len(group),
            "countries": group["entity_id"].nunique(),
            "mean": group[feature].mean() if len(group) else np.nan,
        }

    requested = len(weights)
    valid_count = len(differences)
    minimum_rows = min(by_group[reference]["rows"], by_group[contrast]["rows"])
    minimum_countries = min(
        by_group[reference]["countries"], by_group[contrast]["countries"]
    )
    enough_groups = minimum_rows >= 2 and minimum_countries >= 2
    enough_replicates = valid_count >= max(20, math.ceil(0.80 * requested))

    if not enough_groups:
        status = "insufficient_group_support"
    elif not enough_replicates:
        status = "insufficient_valid_bootstrap_replicates"
    elif minimum_countries < 10 or minimum_rows < 20:
        status = "sparse_group_warning"
    elif minimum_rows / max(by_group[reference]["rows"], by_group[contrast]["rows"]) < 0.10:
        status = "severe_row_imbalance_warning"
    else:
        status = "ok"

    report_interval = enough_groups and enough_replicates
    lower, upper = (
        np.quantile(differences, [0.025, 0.975])
        if report_interval
        else (np.nan, np.nan)
    )
    observed_difference = (
        by_group[contrast]["mean"] - by_group[reference]["mean"]
        if by_group[reference]["rows"] and by_group[contrast]["rows"]
        else np.nan
    )
    return {
        "reference_transition": reference,
        "contrast_transition": contrast,
        "n_rows_reference": by_group[reference]["rows"],
        "n_rows_contrast": by_group[contrast]["rows"],
        "n_countries_reference": by_group[reference]["countries"],
        "n_countries_contrast": by_group[contrast]["countries"],
        "mean_reference": by_group[reference]["mean"],
        "mean_contrast": by_group[contrast]["mean"],
        "mean_difference_contrast_minus_reference": observed_difference,
        "bootstrap_ci_2_5": float(lower),
        "bootstrap_ci_97_5": float(upper),
        "bootstrap_replicates_requested": requested,
        "bootstrap_replicates_valid": valid_count,
        "smallest_to_largest_row_ratio": (
            minimum_rows / max(by_group[reference]["rows"], by_group[contrast]["rows"])
            if max(by_group[reference]["rows"], by_group[contrast]["rows"])
            else np.nan
        ),
        "status": status,
    }


def country_cluster_bootstrap(
    population: pd.DataFrame,
    *,
    n_bootstrap: int = 2000,
    random_seed: int = 20260925,
) -> pd.DataFrame:
    """Country-cluster percentile intervals for prespecified mean contrasts.

    One multinomial draw resamples entire countries and all their years.  The
    same draws are reused for every feature/sample so comparisons are paired.
    Intervals are withheld when a contrast has fewer than two rows/countries in
    either group or fewer than 80% valid bootstrap replicates.
    """
    countries = np.sort(population["entity_id"].astype(str).unique())
    weights = _country_bootstrap_weights(countries, n_bootstrap, random_seed)
    samples = {
        "all_available_per_feature": population,
        "sipri_complete_identical": _sample_frames(population)["sipri_complete_identical"],
    }
    records: list[dict[str, object]] = []
    for sample_name, sample in samples.items():
        for comparison, reference, contrast in COMPARISONS:
            for feature, metadata in FEATURES.items():
                result = _bootstrap_contrast(
                    sample, feature, reference, contrast, countries, weights
                )
                records.append(
                    {
                        "sample": sample_name,
                        "comparison": comparison,
                        "feature": feature,
                        "feature_label": metadata["label"],
                        "unit": metadata["unit"],
                        **result,
                    }
                )
    return pd.DataFrame(records)


def annual_score_trends(population: pd.DataFrame) -> pd.DataFrame:
    records = (
        population.groupby("year", as_index=False)
        .agg(
            n_rows=("entity_id", "size"),
            n_countries=("entity_id", "nunique"),
            trust_mean=("trust_score", "mean"),
            trust_median=("trust_score", "median"),
            trust_q25=("trust_score", lambda values: values.quantile(0.25)),
            trust_q75=("trust_score", lambda values: values.quantile(0.75)),
            threat_mean=("threat_score", "mean"),
            threat_median=("threat_score", "median"),
            threat_q25=("threat_score", lambda values: values.quantile(0.25)),
            threat_q75=("threat_score", lambda values: values.quantile(0.75)),
        )
        .sort_values("year")
    )
    return records


def _ecdf(values: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(values.dropna().astype(float).to_numpy())
    return x, np.arange(1, len(x) + 1) / len(x) if len(x) else np.array([])


def _population_footer(population: pd.DataFrame, extra: str = "") -> str:
    text = (
        f"Population: current UN-member identities; speech years 1990–2024; "
        f"observed current and t+1 UCDP status. N={len(population):,} country-years, "
        f"{population['entity_id'].nunique():,} countries."
    )
    return textwrap.fill(f"{text} {extra}".strip(), width=125)


def _plot_score_ecdfs(population: pd.DataFrame, output_dir: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8), sharey=True)
    for ax, feature in zip(axes, ("trust_score", "threat_score")):
        for transition in TRANSITION_ORDER:
            values = population.loc[population["transition"].eq(transition), feature]
            x, y = _ecdf(values)
            if len(x):
                ax.step(
                    x,
                    y,
                    where="post",
                    color=TRANSITION_COLOURS[transition],
                    linewidth=1.8,
                    label=f"{TRANSITION_LABEL[transition]} (n={len(x):,})",
                )
        ax.set(
            title=FEATURES[feature]["label"],
            xlabel="Independent entailment compatibility score",
            xlim=(0, 1),
            ylim=(0, 1.01),
        )
        ax.grid(alpha=0.22)
    axes[0].set_ylabel("Empirical cumulative proportion")
    axes[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("Complete score distributions across conflict transitions")
    fig.text(
        0.01,
        0.01,
        _population_footer(
            population,
            "ECDFs retain every observation and tail value; the two scores are independent, not competing probabilities.",
        ),
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.95))
    path = output_dir / "score_ecdf_by_conflict_transition.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _plot_spending_ecdf(population: pd.DataFrame, output_dir: Path) -> Path:
    complete = _sample_frames(population)["sipri_complete_identical"]
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    for transition in TRANSITION_ORDER:
        # SIPRI stores proportions. Multiplication is display-only and makes
        # 0.03 appear correctly as 3% of GDP.
        values = 100 * complete.loc[
            complete["transition"].eq(transition), "milex_share_gdp_t"
        ]
        x, y = _ecdf(values)
        if len(x):
            ax.step(
                x,
                y,
                where="post",
                color=TRANSITION_COLOURS[transition],
                linewidth=1.8,
                label=f"{TRANSITION_LABEL[transition]} (n={len(x):,})",
            )
    ax.set(
        title="Observed military burden across conflict transitions",
        xlabel="Military expenditure (% of GDP)",
        ylabel="Empirical cumulative proportion",
        ylim=(0, 1.01),
    )
    ax.grid(alpha=0.22)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    # Keep genuine zeroes and every extreme observation, while making the bulk
    # of the spending distribution readable. No data are trimmed or winsorized.
    ax.set_xscale("symlog", linthresh=1, linscale=1)
    ax.set_xlim(left=0)
    ticks = [0, 0.5, 1, 2, 5, 10, 25, 50, 100]
    ax.set_xticks(ticks, labels=[str(t) for t in ticks])
    ax.set_xlabel("Military expenditure (% of GDP; linear to 1%, logarithmic above)")
    fig.text(
        0.01,
        0.01,
        _population_footer(
            complete,
            "SIPRI-complete identical sample only; missing expenditure is excluded and never treated as zero. ECDFs retain all observed values.",
        ),
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    path = output_dir / "military_spending_ecdf_by_conflict_transition.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def _plot_score_trends(
    population: pd.DataFrame, trends: pd.DataFrame, output_dir: Path
) -> Path:
    fig, (ax, count_ax) = plt.subplots(
        2, 1, figsize=(10.5, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    ax.plot(
        trends["year"], trends["trust_mean"], color="#4C78A8", linewidth=1.8,
        label="Trust/cooperation score (annual mean)",
    )
    ax.plot(
        trends["year"], trends["threat_mean"], color="#E45756", linewidth=1.8,
        label="Threat/security score (annual mean)",
    )
    ax.set(
        title="Whole-speech theme compatibility over time",
        ylabel="Annual mean compatibility score",
        ylim=(0, 1),
    )
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)
    count_ax.bar(trends["year"], trends["n_rows"], color="#9D9D9D", width=0.8)
    count_ax.set(xlabel="Speech year", ylabel="Rows")
    count_ax.grid(axis="y", alpha=0.22)
    fig.text(
        0.01,
        0.01,
        _population_footer(
            population,
            f"Annual denominators are shown below (range {int(trends['n_rows'].min()):,}–{int(trends['n_rows'].max()):,}); 2025 is excluded from substantive trends.",
        ),
        ha="left",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    path = output_dir / "whole_speech_score_trends_1990_2024.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def generate_full_score_eda(
    frame: pd.DataFrame,
    output_dir: str | Path,
    *,
    n_bootstrap: int = 2000,
    random_seed: int = 20260925,
) -> EDAArtifacts:
    """Validate completed scores and write transition-aware EDA artifacts.

    This function performs no model fitting and does not inspect predictive
    performance. Bootstrap intervals are descriptive uncertainty summaries for
    prespecified mean contrasts, not causal estimates or independent-year tests.
    """
    _validate_input(frame)
    population, population_audit = _analysis_population(frame)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    tables: dict[str, pd.DataFrame] = {
        "population_audit": population_audit,
        "transition_counts": transition_counts(population),
        "transition_feature_summaries": feature_summaries(population),
        "country_cluster_bootstrap_differences": country_cluster_bootstrap(
            population, n_bootstrap=n_bootstrap, random_seed=random_seed
        ),
        "annual_score_trends": annual_score_trends(population),
    }
    if "region" in population.columns and population["region"].notna().any():
        region = population.assign(
            region=population["region"].fillna("Missing/unknown").astype(str)
        )
        tables["transition_counts_by_region"] = (
            region.groupby(["region", "transition"], observed=False)
            .agg(n_rows=("entity_id", "size"), n_countries=("entity_id", "nunique"))
            .reset_index()
        )

    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False)

    figures = (
        _plot_score_ecdfs(population, output),
        _plot_spending_ecdf(population, output),
        _plot_score_trends(population, tables["annual_score_trends"], output),
    )

    manifest = {
        "purpose": "transition-aware descriptive EDA after complete whole-speech scoring",
        "score_spec_hash": SPEC_HASH,
        "population": {
            "identity_rule": "main_population == True",
            "speech_years": [1990, 2024],
            "requires_observed_current_conflict": True,
            "requires_observed_next_year_conflict": True,
            "session_80_2025_policy": "excluded from substantive trends and transitions",
            "n_rows": len(population),
            "n_countries": int(population["entity_id"].nunique()),
        },
        "samples": {
            "all_available_per_feature": "Each feature uses every non-missing value in the frozen population.",
            "sipri_complete_identical": "All three features use identical rows with observed SIPRI expenditure.",
        },
        "bootstrap": {
            "method": "country-cluster multinomial bootstrap; all years for a sampled country retained",
            "replicates": n_bootstrap,
            "random_seed": random_seed,
            "interval": "2.5th and 97.5th percentile",
            "minimum_valid_fraction": 0.80,
            "limitations": "Descriptive; does not account for shared global shocks or model-score measurement error.",
        },
        "military_spending": {
            "stored_unit": "proportion of GDP",
            "plot_unit": "percentage points of GDP",
            "missing_values": "excluded, never converted to zero",
        },
        "files": {
            "tables": [f"{name}.csv" for name in tables],
            "figures": [path.name for path in figures],
        },
    }
    manifest_path = output / "eda_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return EDAArtifacts(output, tables, figures, manifest_path)


def run_eda(frame, output_dir):
    """Notebook entry point; returns compact artifact paths instead of all tables."""
    artifacts = generate_full_score_eda(frame, output_dir)
    return {"manifest": str(artifacts.manifest_path),
            "figures": [str(path) for path in artifacts.figures],
            "tables": [str(artifacts.output_dir / (name + ".csv")) for name in artifacts.tables]}


__all__ = [
    "run_eda",
    "EDAArtifacts",
    "FEATURES",
    "TRANSITIONS",
    "annual_score_trends",
    "country_cluster_bootstrap",
    "feature_summaries",
    "generate_full_score_eda",
    "transition_counts",
]
