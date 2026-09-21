# United Nations General Debate Corpus

This project works with the United Nations General Debate Corpus (UNGDC), covering
UN General Debate speeches from 1946 to 2025. The text corpus is stored in
`dataverse_files/TXT/`, and speaker information is stored in
`dataverse_files/Speakers_by_session.xlsx`.

## Setup

Each person must create a local `.env` file in the project root. The `.env` file
should contain the paths to:

1. The directory containing the downloaded data.
2. The `Speakers_by_session.xlsx` file.

Use absolute paths so that the notebook works regardless of the current working
directory. For example:

```env
data_path=/absolute/path/to/code/dataverse_files
xlsx_path=/absolute/path/to/code/dataverse_files/Speakers_by_session.xlsx
```

Replace `/absolute/path/to/code` with the location of this project on your
computer. Do not commit `.env`, since paths are different for every person and
may contain private information.

## Data layout

```text
dataverse_files/
├── Speakers_by_session.xlsx
└── TXT/
	├── Session 01 - 1946/
	├── Session 02 - 1947/
	└── ...
```

The dataset documentation is available in
[`dataverse_files/README.txt`](dataverse_files/README.txt).

## Running the project

1. Create and activate a virtual environment.
2. Install the required Python packages.
3. Add your local paths to `.env` as described above.
4. Open and run `main.ipynb`.
