"""Run the complete predictive analysis and save its tables and figure.

Requires outputs/prepared.parquet and outputs/ucdp_country_year.parquet
(scripts/prepare_analysis.py) and the shared outputs/rhetoric_full.sqlite cache.
Writes to outputs/prediction/ and copies the small tables/figure to results/prediction/.
No transformer inference is repeated.
"""
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import numpy as np

from analysis_prediction import (build_modelling_table, coefficient_table, load_inputs,
                                 plot_rounds, run_final_evaluation, run_validation_rounds,
                                 summary_table)


def main():
    output = ROOT / "outputs/prediction"
    published = ROOT / "results/prediction"
    output.mkdir(parents=True, exist_ok=True)
    published.mkdir(parents=True, exist_ok=True)

    data = build_modelling_table(*load_inputs(ROOT))
    print(f"Modelling table: {len(data)} country-years, {data['entity_id'].nunique()} countries, "
          f"{data['milex_share_gdp_t'].notna().sum()} with observed spending", flush=True)

    rounds = run_validation_rounds(data)
    final, models = run_final_evaluation(data)
    coefficients = coefficient_table(models)

    files = {
        "validation_rounds_scores.csv": rounds.round(4),
        "validation_rounds_ap_all.csv": summary_table(rounds, "AP_all").round(3),
        "validation_rounds_ap_peaceful.csv": summary_table(rounds, "AP_peaceful").round(3),
        "final_2021_2024_scores.csv": final.round(4),
        "final_coefficients.csv": coefficients.round(4),
        "final_odds_ratios.csv": np.exp(coefficients).round(3),
    }
    for name, table in files.items():
        index = name in {"validation_rounds_ap_all.csv", "validation_rounds_ap_peaceful.csv",
                         "final_coefficients.csv", "final_odds_ratios.csv"}
        table.to_csv(output / name, index=index)
    plot_rounds(rounds, final, output / "prediction_ap_by_period.png")

    for path in output.iterdir():
        shutil.copy2(path, published / path.name)

    print(summary_table(rounds, "AP_all").round(3).to_string())
    print(final[["sample", "model", "AP_all", "ROC_AUC_all", "AP_peaceful"]].round(3).to_string())
    print(f"Saved {len(files) + 1} files to {output} and {published}", flush=True)


if __name__ == "__main__":
    main()
