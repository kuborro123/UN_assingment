# UN speeches, rhetoric and conflict

A data-science project combining UN General Debate speeches, UCDP/PRIO armed-conflict data, and SIPRI military-expenditure data to study conflict transitions and next-year prediction.

## Run the notebook

Use Python 3.11. Install the listed packages with `pip install -r requirements.txt`, then open `main.ipynb` from the project folder in your ide select **Restart Kernel and Run All**. The package list covers the analysis; install a notebook interface separately if needed.

The notebook expects these inputs at these paths:

- `TXT/` — UN speech text files
- `Speakers_by_session.xlsx` — speaker metadata
- `UcdpPrioConflict_v26_1.csv` — UCDP/PRIO data
- `SIPRI-Milex-data-1949-2025_v1.2.xlsx` — SIPRI data
- `outputs/rhetoric_full.sqlite` — completed rhetoric-score cache

These data files and the score cache are not included in the repository. The notebook uses the cache and does not run transformer inference. It writes tables and figures to `outputs/submission/`.

The raw sources are available from the [UN General Debate Corpus on Harvard Dataverse](https://doi.org/10.7910/DVN/0TJX8Y), the [UCDP download centre](https://ucdp.uu.se/downloads/) (UCDP/PRIO Armed Conflict Dataset v26.1), and the [SIPRI Military Expenditure Database](https://www.sipri.org/databases/milex) (1949--2025 workbook, Share of GDP sheet). Use the filenames and versions above; later releases are likely not to reproduce the same counts.

## If you do not have the score cache

Ask us specifically to share `rhetoric_full.sqlite`, and place it in `outputs/`. We also uploaded it to:
https://drive.google.com/drive/folders/1Ach27hl0Fv4v5MpKTQG63gh2urtSwI1h?usp=share_link

Alternatively, the cache can be regenerated with the full project repo and the source data in place. The following scripts are **not** part of our submission for assignment 1:

```bash
pip install -r requirements-model.txt
python scripts/prepare_analysis.py
python scripts/score_speeches.py --device auto --batch-size 8
```

Scoring requires downloading the model and can take many hours; it took about ten hours on the original Mac. The script resumes compatible completed batches. Do not run two scoring processes against the same cache.

See `data-manifest.md` for the source-file versions and `report_guidelines.md` for the report rubric and requirements.
