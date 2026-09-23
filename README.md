# United Nations General Debate Corpus

This project analyzes United Nations General Debate speeches from 1946 to 2025.
The notebook combines speech text and speaker metadata with UCDP/PRIO conflict
data and SIPRI military expenditure data. The exploratory analysis focuses on
1990–2025 and compares trust/cooperation rhetoric, military-threat rhetoric, and
military spending with conflict status in the following year.

## Setup

Create a local `.env` file in the project root. Use absolute paths so that the
notebook works regardless of the current working directory. It must contain all
four paths used by `main.ipynb`:

```env
data_path=/absolute/path/to/code/dataverse_files
speech_path=/absolute/path/to/code/dataverse_files/Speakers_by_session.xlsx
conflicts_path=/absolute/path/to/code/dataverse_files/conflicts.csv
sipri_path=/absolute/path/to/SIPRI-Milex-data-1949-2025_v1.2.xlsx
```

Replace `/absolute/path/to/code` with the location of this project on your
computer and update the SIPRI path to the location of your downloaded workbook.
Do not commit `.env`, since paths are different for every person and may contain
private information.

The notebook loads these environment variables into `DATA_PATH`, `SPEECH_PATH`,
`CONFLICTS_PATH`, and `SIPRI_PATH` at startup.

## Data layout

```text
dataverse_files/
├── Speakers_by_session.xlsx
├── conflicts.csv
└── TXT/
	├── Session 01 - 1946/
	├── Session 02 - 1947/
	└── ...
```

The SIPRI workbook is separate from the UN corpus directory and should contain
the `Share of GDP` sheet used by the notebook. The dataset documentation is
available in [`dataverse_files/README.txt`](dataverse_files/README.txt).

## What the notebook does

`main.ipynb`:

1. Loads the four input paths from `.env`.
2. Adds speech text to the speaker metadata and cleans missing metadata.
3. Loads and aggregates UCDP conflict data by country and year.
4. Loads SIPRI military spending as a percentage of GDP and reshapes it to
   country-year format.
5. Standardizes country names and flags historical entities that cannot be
   matched reliably to modern country data.
6. Merges the datasets and restricts the modeling table to 1990–2025.
7. Cleans speech text and removes English stopwords.
8. Scores each speech with the
   `MoritzLaurer/ModernBERT-large-zeroshot-v2.0` zero-shot classification model
   for trust/cooperation and military-threat rhetoric.
9. Compares those scores and military spending with whether conflict occurs in
   the following year.

The classification step can take approximately one hour and requires a working
PyTorch/Transformers installation. On macOS, the notebook is configured to use
the Apple Metal Performance Shaders (`mps`) device.

## Output

The notebook saves the processed and scored dataset as `merged_data.csv` in the
project root. Because this file contains generated results, it can be reused to
inspect the final data without rebuilding the earlier processing steps.

## Running the project

1. Create and activate a virtual environment.
2. Install the required Python packages:

   ```bash
   pip install python-dotenv pandas openpyxl nltk scipy matplotlib seaborn transformers torch
   ```

3. Add your local paths to `.env` as described above.
4. Open `main.ipynb` and run the cells from top to bottom.
