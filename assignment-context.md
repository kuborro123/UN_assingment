# Fundamentals of Data Science: Assignment Context

This file is the durable project brief. Use it when choosing questions, extending
`main.ipynb`, and writing the final LaTeX report.

## Approved scope, 25 September 2026

The student approved the audited transition-aware design in
`RESEARCH_DESIGN.md`, retaining SDG 16 and zero-shot theme features. They explicitly
confirmed that Session 81 / 2026 does not need to be integrated. Do not collect it.
This records the student's instruction, not an independently received TA answer.
The recent-text requirement is addressed using the supplied Session 80 material;
2025 has no next-year target and unresolved transcript boilerplate requires it to
remain separate from primary substantive text comparisons.

## Project objective

Perform exploratory data analysis (collection, preparation, dataset combination,
descriptive statistics, and visualisation) and predictive analysis (model
selection, training, and validation) using the UN General Debate Corpus. The
analysis must combine speeches with at least two external datasets, address the
2026 General Debate theme, and explicitly connect to one Sustainable Development
Goal (SDG).

## Required research framing

- 2026 theme: **"Restoring trust, managing transformation"**.
- Choose and justify **one SDG**.
- Pose **one exploratory question** and **one predictive question** appropriate
  for the combined data.
- State and justify hypotheses for both questions before presenting results.
- Let the EDA motivate or refine the predictive question.
- Explain why the questions matter and how they connect to both the theme and
  chosen SDG. Original questions are rewarded.
- Discuss the proposed questions with a TA before committing to the analysis.

## Data requirements

- Primary source: raw UN General Debate statement text, 1946–2025 (Sessions
  1–80), with speaker metadata.
- Combine the speeches with **at least two other well-sourced datasets**.
- Current external sources in this repository are the UCDP/PRIO Armed Conflict
  Dataset and SIPRI Military Expenditure Database.
- Collect and use **recent textual data**. Because the supplied corpus ends in
  2025 while the rubric explicitly asks for recent text and the 2026 debate is
  taking place during the course, confirm with the TA whether this requires
  collecting Session 81 statements. Document the source, retrieval date, and
  inclusion rule for any collected 2026 texts.
- Cite the UN corpus documentation/paper and every external dataset, including
  dataset versions, coverage, units, and public download links where possible.
- Inspect raw records and discuss original data issues rather than treating the
  data as analysis-ready.

## Analysis and reproducibility requirements

- Explain text cleaning and feature construction, country/entity reconciliation,
  temporal alignment, exclusions, missingness, and aggregation choices.
- Preserve a clear distinction between missing data, true zeroes, and records
  outside a source's coverage.
- Apply statistical learning and report interpretable coefficients and/or
  suitable out-of-sample validation metrics.
- Justify model choice, baseline, validation design, and metrics; acknowledge
  model advantages, assumptions, and limitations.
- Avoid leakage. For observations repeated across countries and years, prefer a
  split strategy that respects the prediction target and temporal/group
  structure rather than an unjustified random row split.
- Include effective, accurate, informative visualisations that follow lecture
  best practices and can stand alone through titles, labels, units, legends, and
  captions.
- Ensure `main.ipynb` runs from scratch and records package/data requirements.
  Do not rely solely on private absolute paths; provide public links or clear
  download instructions for raw external data.
- Python/NumPy/Pandas/Matplotlib/scikit-learn are expected course tools, but
  other software is permitted. TA implementation support may be unavailable for
  other software.

## Report and submission

- Submit one `.zip` containing the PDF report and analysis code (for example,
  `main.ipynb`).
- Target approximately 7 pages; the hard maximum is 9 pages excluding
  references. Pages beyond the limit are not read and incur a penalty.
- Use the provided template without changing font size, spacing, or columns.
- Expected structure: Title; Author List in alphabetical order; Abstract;
  Introduction; Methodology; Results and Discussion; Conclusion; References.
  Related work may be integrated into the introduction/methodology or placed in
  its own section.
- The report must contain enough information to understand the analysis and
  results without relying on the notebook.
- Include only contributors in the author list. Listed authors are assumed to
  have contributed equally.
- Hard deadline: **Monday, 28 September 2026 at 23:59**. No submission receives
  0/100. Multiple submissions are allowed, so make an early safety submission;
  the course recommends having the work ready by Friday.
- Work must be original and is subject to plagiarism detection and UvA rules.

## Rubric checklist

- **Question and Hypothesis:** One suitable exploratory question and one suitable
  predictive question; justified hypotheses; explicit link to one SDG;
  originality and creativity.
- **Data Preparation:** Dataset properties and original data issues are
  discussed; cleaning and preparation are reasonable; speeches are combined
  with at least two other datasets; recent textual data are collected and used.
- **Data Visualisation:** Visualisations are effective, accurate, informative,
  and follow lecture best practices.
- **Context:** The report demonstrates how the data were collected, what they
  mean, and why the problem is justified.
- **Model Selection and Validation:** Models are justified with advantages and
  limitations; analysis is sound; metrics and validation are appropriate.
- **Limitations:** The report identifies where and why the analysis is limited,
  proposes concrete improvements, and cites related methodological literature.
- **Report Quality:** The report is well structured, clear, well written, and
  free of typos.
- **Creativity:** Meeting baseline criteria alone does not guarantee the highest
  grade; distinctive questions and thoughtful analytical choices are rewarded.

## Pre-submission quality gate

- Both questions, hypotheses, theme link, and SDG link appear explicitly in the
  report.
- At least three datasets are genuinely used in the analysis, not merely loaded.
- Recent text is included and its provenance is documented, or the TA's written
  interpretation of this requirement is recorded.
- Cleaning and merge decisions are quantified and auditable.
- Predictive performance is compared with a defensible baseline on unseen data.
- Claims match the analysis and avoid causal language unless the design supports
  it.
- Limitations include concrete remedies and methodological citations.
- Every figure is readable at final PDF size.
- The notebook restarts and runs end-to-end; the final PDF respects the template
  and page limit; the ZIP opens and contains both required deliverables.
