"""Reproducible data preparation and Milestone 1 text analysis.

The functions in this module deliberately stop before predictive modelling.  In
particular, the final 2022--2025 target period is not inspected here beyond basic
data-completeness checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import unicodedata
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pycountry
from dotenv import load_dotenv

from text_dictionaries import DICTIONARY_VERSION, TEXT_DICTIONARIES


CONFIG_DIR = Path(__file__).resolve().parent / "config"
SPEECH_ENTITY_RULES = pd.read_csv(CONFIG_DIR / "speech_entity_rules.csv")
SESSION_PATTERN = re.compile(r"Session (?P<session>\d{2}) - (?P<year>\d{4})$")
SPEECH_FILE_PATTERN = re.compile(
    r"(?P<source_iso>[A-Z]{2,3})_(?P<session>\d{1,2})_(?P<year>\d{4})\.txt$"
)
TOKEN_PATTERN = re.compile(r"(?u)[^\W\d_]+(?:[-\u2019'][^\W\d_]+)*")
INTRO_PATTERN = re.compile(
    r"(?is)^.{0,900}?\b(?:invite|invited)\s+"
    r"(?:him|her|his excellency|her excellency|his majesty|her majesty)\s+"
    r"to\s+(?:address|speak before)\s+(?:the\s+)?assembly\s*[.!?]\s*"
)
OUTRO_PATTERN = re.compile(
    r"(?is)\b(?:and\s+)?on behalf of (?:the\s+)?(?:general\s+)?assembly"
    r"\s*,?\s*i\s+(?:wish to\s+)?thank\b"
)

DISPLAY_NAME_OVERRIDES = {
    "BOL": "Bolivia",
    "BRN": "Brunei",
    "COD": "Congo, Democratic Republic of the",
    "COG": "Congo, Republic of the",
    "CZE": "Czechia",
    "GBR": "United Kingdom",
    "IRN": "Iran",
    "KOR": "Korea, South",
    "LAO": "Laos",
    "MDA": "Moldova",
    "PRK": "Korea, North",
    "RUS": "Russia",
    "SYR": "Syria",
    "TZA": "Tanzania",
    "USA": "United States",
    "VEN": "Venezuela",
    "VNM": "Vietnam",
    "SUN": "Soviet Union",
    "BYSSR": "Byelorussian Soviet Socialist Republic",
    "UASSR": "Ukrainian Soviet Socialist Republic",
}

@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    speech_dir: Path
    metadata_path: Path
    conflicts_path: Path
    sipri_path: Path
    output_dir: Path

    @classmethod
    def from_env(cls, root: str | Path | None = None) -> "ProjectPaths":
        project_root = Path(root or Path(__file__).resolve().parent).resolve()
        load_dotenv(project_root / ".env", override=False)

        configured_data = Path(os.getenv("data_path", project_root / "TXT")).expanduser()
        if configured_data.name != "TXT" and (configured_data / "TXT").is_dir():
            configured_data = configured_data / "TXT"

        return cls(
            root=project_root,
            speech_dir=configured_data.resolve(),
            metadata_path=Path(
                os.getenv("speech_path", project_root / "Speakers_by_session.xlsx")
            ).expanduser().resolve(),
            conflicts_path=Path(
                os.getenv("conflicts_path", project_root / "UcdpPrioConflict_v26_1.csv")
            ).expanduser().resolve(),
            sipri_path=Path(
                os.getenv(
                    "sipri_path",
                    project_root / "SIPRI-Milex-data-1949-2025_v1.2.xlsx",
                )
            ).expanduser().resolve(),
            output_dir=Path(
                os.getenv("output_path", project_root / "outputs")
            ).expanduser().resolve(),
        )

    def validate(self) -> None:
        required = {
            "speech directory": self.speech_dir,
            "speaker metadata": self.metadata_path,
            "UCDP data": self.conflicts_path,
            "SIPRI data": self.sipri_path,
        }
        missing = [f"{label}: {path}" for label, path in required.items() if not path.exists()]
        if missing:
            raise FileNotFoundError("Missing required inputs:\n" + "\n".join(missing))


@dataclass
class PipelineResult:
    analysis: pd.DataFrame
    speeches: pd.DataFrame
    sipri: pd.DataFrame
    conflicts: pd.DataFrame
    audits: dict[str, pd.DataFrame]


def _normalise_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def canonical_country_name(entity_id: str) -> str:
    if entity_id in DISPLAY_NAME_OVERRIDES:
        return DISPLAY_NAME_OVERRIDES[entity_id]
    country = pycountry.countries.get(alpha_3=entity_id)
    return country.name if country else entity_id


def _combine_unique(values: Iterable[object]) -> object:
    clean = sorted({str(value).strip() for value in values if pd.notna(value) and str(value).strip()})
    return " | ".join(clean) if clean else pd.NA


def _speech_rule(source_iso: str, year: int) -> pd.Series | None:
    match = SPEECH_ENTITY_RULES[
        SPEECH_ENTITY_RULES["source_label"].eq(source_iso)
        & SPEECH_ENTITY_RULES["valid_from"].le(year)
        & SPEECH_ENTITY_RULES["valid_to"].ge(year)
    ]
    if len(match) > 1:
        raise AssertionError(f"Overlapping speech entity rules for {source_iso} in {year}")
    return None if match.empty else match.iloc[0]


def _speech_entity_id(source_iso: str, year: int) -> str:
    rule = _speech_rule(source_iso, year)
    return source_iso if rule is None else str(rule["entity_id"])


def _speech_entity_status(source_iso: str, entity_id: str, year: int) -> tuple[str, bool]:
    rule = _speech_rule(source_iso, year)
    if rule is not None:
        entity_type = str(rule["entity_type"])
        if entity_type == "observer_state" and entity_id == "PSE":
            return "sensitivity_observer", False
        if entity_type == "observer_state":
            return "excluded_observer_no_sipri", False
        if entity_type == "non_state_aggregate":
            return "excluded_non_state", False
        return "excluded_historical", False
    if entity_id == "EU":
        return "excluded_non_state", False
    if entity_id == "VAT":
        return "excluded_observer_no_sipri", False
    if entity_id == "PSE":
        return "sensitivity_observer", False
    if entity_id in {"CSK", "DDR", "YUG", "YMD", "SUN", "BYSSR", "UASSR"}:
        return "excluded_historical", False
    if pycountry.countries.get(alpha_3=entity_id) is None:
        return "unresolved_iso", False
    return "main_un_member", True


def load_speeches(paths: ProjectPaths) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    metadata = pd.read_excel(paths.metadata_path)
    required = {
        "Year",
        "Session",
        "ISO Code",
        "Country",
        "Name of Person Speaking",
        "Post",
    }
    missing_columns = required.difference(metadata.columns)
    if missing_columns:
        raise ValueError(f"Speaker metadata lacks columns: {sorted(missing_columns)}")

    metadata = metadata[list(required)].copy()
    metadata = metadata.rename(
        columns={
            "Year": "year",
            "Session": "session",
            "ISO Code": "source_iso",
            "Country": "country_name_raw",
            "Name of Person Speaking": "speaker_name",
            "Post": "speaker_post_raw",
        }
    )
    metadata["source_iso_raw"] = metadata["source_iso"].astype("string").str.strip()
    metadata["source_iso"] = metadata["source_iso_raw"]
    metadata["year"] = pd.to_numeric(metadata["year"], errors="raise").astype(int)
    metadata["session"] = pd.to_numeric(metadata["session"], errors="raise").astype(int)
    metadata["country_name_raw"] = metadata["country_name_raw"].astype("string").str.strip()

    metadata_corrections = pd.read_csv(CONFIG_DIR / "metadata_key_corrections.csv")
    for correction in metadata_corrections.itertuples(index=False):
        bad_iso = correction.metadata_iso
        session = int(correction.session)
        year = int(correction.year)
        corrected_iso = correction.file_iso
        correction_mask = (
            metadata["source_iso_raw"].eq(bad_iso)
            & metadata["session"].eq(session)
            & metadata["year"].eq(year)
        )
        if correction_mask.sum() != 1:
            raise AssertionError(
                f"Expected one metadata row for correction {(bad_iso, session, year)}; "
                f"found {int(correction_mask.sum())}"
            )
        metadata.loc[correction_mask, "source_iso"] = corrected_iso

    key = ["source_iso", "session", "year"]
    duplicate_metadata = metadata[metadata.duplicated(key, keep=False)].sort_values(key)
    metadata_agg = (
        metadata.groupby(key, as_index=False, dropna=False)
        .agg(
            source_iso_raw=("source_iso_raw", _combine_unique),
            country_name_raw=("country_name_raw", _combine_unique),
            speaker_name=("speaker_name", _combine_unique),
            speaker_post_raw=("speaker_post_raw", _combine_unique),
            metadata_rows=("year", "size"),
        )
    )
    metadata_agg["metadata_ambiguous"] = metadata_agg["metadata_rows"].gt(1)

    session_dirs = []
    invalid_session_dirs = []
    for path in sorted(paths.speech_dir.iterdir()):
        if not path.is_dir():
            continue
        match = SESSION_PATTERN.fullmatch(path.name)
        if match:
            session_dirs.append((path, int(match.group("session")), int(match.group("year"))))
        else:
            invalid_session_dirs.append({"path": str(path), "reason": "directory name does not match session pattern"})

    if len(session_dirs) != 80:
        raise AssertionError(f"Expected exactly 80 valid session directories; found {len(session_dirs)}")

    speech_records = []
    invalid_files = []
    for session_path, parent_session, parent_year in session_dirs:
        for text_path in sorted(session_path.glob("*.txt")):
            match = SPEECH_FILE_PATTERN.fullmatch(text_path.name)
            if not match:
                invalid_files.append({"path": str(text_path), "reason": "filename does not match ISO_session_year pattern"})
                continue
            file_session = int(match.group("session"))
            file_year = int(match.group("year"))
            if file_session != parent_session or file_year != parent_year:
                invalid_files.append({"path": str(text_path), "reason": "filename and parent session disagree"})
                continue
            try:
                text = text_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                invalid_files.append({"path": str(text_path), "reason": "not valid UTF-8"})
                continue
            speech_records.append(
                {
                    "source_iso": match.group("source_iso"),
                    "session": file_session,
                    "year": file_year,
                    "speech_path": str(text_path.relative_to(paths.speech_dir)),
                    "speech_raw": text,
                }
            )

    files = pd.DataFrame(speech_records)
    duplicate_files = files[files.duplicated(key, keep=False)].sort_values(key)
    if not duplicate_files.empty:
        raise AssertionError("Duplicate speech files found for the same ISO/session/year key")

    file_keys = files[key].drop_duplicates()
    metadata_keys = metadata_agg[key].drop_duplicates()
    unmatched_files = files.merge(metadata_keys, on=key, how="left", indicator=True)
    unmatched_files = unmatched_files[unmatched_files["_merge"].eq("left_only")].drop(columns="_merge")
    metadata_without_speech = metadata_agg.merge(file_keys, on=key, how="left", indicator=True)
    metadata_without_speech = metadata_without_speech[
        metadata_without_speech["_merge"].eq("left_only")
    ].drop(columns="_merge")

    # Speech files define observations and country identity.  Metadata only adds
    # speaker information, so a missing metadata row must not delete a speech.
    speeches = files.merge(metadata_agg, on=key, how="left", validate="one_to_one")
    speeches["metadata_rows"] = speeches["metadata_rows"].fillna(0).astype(int)
    speeches["metadata_ambiguous"] = speeches["metadata_rows"].gt(1)
    speeches["entity_id"] = speeches.apply(
        lambda row: _speech_entity_id(str(row.source_iso), int(row.year)), axis=1
    )
    status = speeches.apply(
        lambda row: _speech_entity_status(row.source_iso, row.entity_id, int(row.year)),
        axis=1,
        result_type="expand",
    )
    speeches[["entity_status", "main_population"]] = status
    speeches["country_name"] = speeches["entity_id"].map(canonical_country_name)
    speeches["speaker_post_group"] = speeches["speaker_post_raw"].map(group_speaker_post)

    audits = {
        "metadata_key_corrections": metadata_corrections,
        "metadata_duplicate_keys": duplicate_metadata,
        "duplicate_speech_files": duplicate_files,
        "invalid_speech_files": pd.DataFrame(invalid_files, columns=["path", "reason"]),
        "invalid_session_directories": pd.DataFrame(
            invalid_session_dirs, columns=["path", "reason"]
        ),
        "unmatched_speech_files": unmatched_files,
        "metadata_without_speech": metadata_without_speech,
    }
    return speeches.sort_values(["year", "entity_id"]).reset_index(drop=True), audits


def group_speaker_post(value: object) -> str:
    if pd.isna(value) or not str(value).strip():
        return "unknown"
    post = _normalise_name(value)
    if re.search(r"\b(prime minister|head of government|chancellor)\b", post):
        return "head_of_government"
    if re.search(r"\b(president|king|queen|emir|amir|prince|head of state)\b", post):
        return "head_of_state"
    if re.search(r"\b(foreign affairs|external affairs|foreign minister)\b", post):
        return "foreign_minister"
    if re.search(r"\b(representative|delegation|ambassador)\b", post):
        return "representative"
    return "other"


def load_sipri(paths: ProjectPaths) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_excel(paths.sipri_path, sheet_name="Share of GDP", header=5, dtype=object)
    year_columns = [column for column in raw.columns if isinstance(column, (int, np.integer))]
    if year_columns != list(range(1949, 2026)):
        raise AssertionError("Unexpected SIPRI Share of GDP year columns")

    candidates = raw[raw[year_columns].notna().any(axis=1) & raw["Country"].notna()].copy()
    crosswalk = pd.read_csv(CONFIG_DIR / "sipri_country_crosswalk.csv")
    source_names = set(candidates["Country"].astype(str))
    crosswalk_names = set(crosswalk["source_name"].astype(str))
    if source_names != crosswalk_names:
        raise AssertionError(
            "SIPRI source labels differ from the reviewed crosswalk. "
            f"New={sorted(source_names - crosswalk_names)}, "
            f"missing={sorted(crosswalk_names - source_names)}"
        )
    unresolved = crosswalk[crosswalk["exclusion_status"].eq("unresolved")]
    if not unresolved.empty:
        raise AssertionError(f"Unresolved SIPRI names: {unresolved.source_name.tolist()}")

    mapped = candidates.merge(
        crosswalk[["source_name", "entity_id", "exclusion_status"]],
        left_on="Country",
        right_on="source_name",
        how="left",
        validate="one_to_one",
    )
    mapped = mapped[mapped["exclusion_status"].eq("included")].copy()
    long = mapped.melt(
        id_vars=["entity_id", "Country"],
        value_vars=year_columns,
        var_name="year",
        value_name="source_value",
    )
    long["year"] = long["year"].astype(int)

    def status(value: object) -> str:
        if isinstance(value, (int, float, np.integer, np.floating)) and pd.notna(value):
            return "observed"
        marker = str(value).strip() if pd.notna(value) else ""
        if marker == "xxx":
            return "not_independent_or_nonexistent"
        if marker in {"...", "..", ". ."}:
            return "unavailable"
        return "blank"

    long["milex_status_t"] = long["source_value"].map(status)
    long["milex_share_gdp_t"] = pd.to_numeric(long["source_value"], errors="coerce")
    long = long.rename(columns={"Country": "sipri_country_name"})
    long = long.drop(columns="source_value")
    if long.duplicated(["entity_id", "year"]).any():
        raise AssertionError("SIPRI mapping produced duplicate entity-year rows")
    return long.sort_values(["entity_id", "year"]).reset_index(drop=True), crosswalk


def load_ucdp(paths: ProjectPaths) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(paths.conflicts_path)
    required = {"conflict_id", "location", "year", "intensity_level"}
    if missing := required.difference(raw.columns):
        raise ValueError(f"UCDP data lacks columns: {sorted(missing)}")
    if (raw["year"].min(), raw["year"].max()) != (1946, 2025):
        raise AssertionError("Unexpected UCDP year coverage")

    exploded = raw.assign(source_name=raw["location"].str.split(", ")).explode("source_name")
    exploded["source_name"] = exploded["source_name"].str.strip()
    crosswalk = pd.read_csv(CONFIG_DIR / "ucdp_country_crosswalk.csv")
    raw_names = set(exploded["source_name"].astype(str))
    crosswalk_names = set(crosswalk["source_name"].astype(str))
    if raw_names != crosswalk_names:
        raise AssertionError(
            "UCDP source labels differ from the reviewed crosswalk. "
            f"New={sorted(raw_names - crosswalk_names)}, "
            f"missing={sorted(crosswalk_names - raw_names)}"
        )
    exploded = exploded.reset_index(drop=True).reset_index(names="source_row_id")
    exploded = exploded.merge(crosswalk, on="source_name", how="left", validate="many_to_many")
    exploded = exploded[
        exploded["year"].between(exploded["valid_from"], exploded["valid_to"])
    ].copy()
    match_counts = exploded.groupby("source_row_id").size()
    if len(match_counts) != len(raw.assign(source_name=raw["location"].str.split(", ")).explode("source_name")):
        raise AssertionError("At least one UCDP row has no time-valid crosswalk mapping")
    if not match_counts.eq(1).all():
        raise AssertionError("At least one UCDP row has overlapping crosswalk mappings")

    included = exploded[exploded["exclusion_status"].eq("included")].copy()
    conflicts = (
        included.groupby(["entity_id", "year"], as_index=False)
        .agg(
            conflict_active_t=("conflict_id", lambda values: 1),
            max_intensity_t=("intensity_level", "max"),
            n_conflicts_t=("conflict_id", "nunique"),
            any_war_t=("intensity_level", lambda values: int((values == 2).any())),
        )
    )
    if conflicts.duplicated(["entity_id", "year"]).any():
        raise AssertionError("UCDP aggregation produced duplicate entity-year rows")
    exclusions = exploded[exploded["exclusion_status"].eq("excluded")].copy()
    return conflicts, crosswalk, exclusions


def clean_speech_text(text: object, year: int | None = None) -> tuple:
    raw = "" if pd.isna(text) else str(text)
    bom_count = raw.count("\ufeff")
    soft_hyphen_count = raw.count("\u00ad")
    replacement_character_count = raw.count("\ufffd")
    cleaned = unicodedata.normalize("NFKC", raw).replace("\ufeff", "").replace("\u00ad", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"-[ \t]*\n[ \t]*", "-", cleaned)

    intro_removed = False
    outro_removed = False
    removed = 0
    if year == 2025:
        intro_match = INTRO_PATTERN.match(cleaned)
        if intro_match:
            removed += intro_match.end()
            cleaned = cleaned[intro_match.end() :]
            intro_removed = True
        tail_start = max(0, len(cleaned) - 1500)
        outro_match = OUTRO_PATTERN.search(cleaned, pos=tail_start)
        if outro_match:
            removed += len(cleaned) - outro_match.start()
            cleaned = cleaned[: outro_match.start()]
            outro_removed = True
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (
        cleaned,
        intro_removed or outro_removed,
        removed,
        intro_removed,
        outro_removed,
        bom_count,
        soft_hyphen_count,
        replacement_character_count,
    )


def _dictionary_pattern(terms: Iterable[str]) -> re.Pattern[str]:
    alternatives = []
    for term in sorted(set(terms), key=len, reverse=True):
        escaped = re.escape(term).replace(r"\ ", r"\s+")
        alternatives.append(escaped)
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + r")(?!\w)", re.IGNORECASE)


DICTIONARY_PATTERNS = {
    name: _dictionary_pattern(terms) for name, terms in TEXT_DICTIONARIES.items()
}


def _count_dictionary_matches(category: str, text: str) -> int:
    matches = list(DICTIONARY_PATTERNS[category].finditer(text))
    if category != "trust_dialogue_salience":
        return len(matches)
    count = 0
    excluded_following = re.compile(r"^\s+(?:that|funds?|territor(?:y|ies))\b", re.IGNORECASE)
    for match in matches:
        if match.group(0).casefold() == "trust" and excluded_following.search(text[match.end() :]):
            continue
        count += 1
    return count


def add_text_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    cleaned = result.apply(
        lambda row: clean_speech_text(row["speech_raw"], int(row["year"])), axis=1
    )
    result[
        [
            "speech_clean",
            "boilerplate_removed",
            "boilerplate_chars_removed",
            "intro_boilerplate_removed",
            "outro_boilerplate_removed",
            "source_bom_count",
            "source_soft_hyphen_count",
            "source_replacement_character_count",
        ]
    ] = pd.DataFrame(
        cleaned.tolist(), index=result.index
    )
    result["boilerplate_review_needed"] = result["year"].eq(2025) & ~result[
        "intro_boilerplate_removed"
    ]
    result["speech_token_count"] = result["speech_clean"].map(
        lambda value: len(TOKEN_PATTERN.findall(value.casefold()))
    )
    if result["speech_token_count"].le(0).any():
        raise AssertionError("Text cleaning produced an empty speech")

    for category in DICTIONARY_PATTERNS:
        count_column = f"dict_{category}_count"
        rate_column = f"dict_{category}_per_1k"
        result[count_column] = result["speech_clean"].map(
            lambda value, category=category: _count_dictionary_matches(category, value)
        )
        result[rate_column] = 1000 * result[count_column] / result["speech_token_count"]
    result["dictionary_version"] = DICTIONARY_VERSION
    return result


def build_analysis(paths: ProjectPaths | None = None) -> PipelineResult:
    paths = paths or ProjectPaths.from_env()
    paths.validate()
    speeches, speech_audits = load_speeches(paths)
    sipri, sipri_crosswalk = load_sipri(paths)
    conflicts, ucdp_crosswalk, ucdp_exclusions = load_ucdp(paths)

    scoped = speeches[speeches["year"].between(1990, 2025)].copy()
    if scoped.duplicated(["entity_id", "year"]).any():
        duplicates = scoped[scoped.duplicated(["entity_id", "year"], keep=False)]
        raise AssertionError(
            "Canonical speech keys are not unique:\n"
            + duplicates[["entity_id", "year", "speech_path"]].to_string(index=False)
        )

    expected_rows = len(scoped)
    analysis = scoped.merge(conflicts, on=["entity_id", "year"], how="left", validate="one_to_one")
    if len(analysis) != expected_rows:
        raise AssertionError("UCDP merge changed the speech row count")

    conflict_columns = ["conflict_active_t", "max_intensity_t", "n_conflicts_t", "any_war_t"]
    main_mask = analysis["main_population"]
    analysis.loc[main_mask, conflict_columns] = analysis.loc[main_mask, conflict_columns].fillna(0)
    analysis.loc[main_mask, conflict_columns] = analysis.loc[main_mask, conflict_columns].astype(int)
    analysis["ucdp_status_t"] = np.where(
        analysis["main_population"],
        np.where(analysis["conflict_active_t"].eq(1), "observed_conflict", "observed_no_conflict"),
        "not_main_population",
    )

    analysis = analysis.merge(sipri, on=["entity_id", "year"], how="left", validate="one_to_one")
    if len(analysis) != expected_rows:
        raise AssertionError("SIPRI merge changed the speech row count")
    analysis["milex_status_t"] = analysis["milex_status_t"].fillna("no_country_row")

    future = conflicts.rename(
        columns={
            "year": "target_year",
            "conflict_active_t": "conflict_active_t1",
        }
    )[["entity_id", "target_year", "conflict_active_t1"]]
    analysis["target_year"] = analysis["year"] + 1
    analysis = analysis.merge(future, on=["entity_id", "target_year"], how="left", validate="one_to_one")
    target_mask = analysis["main_population"] & analysis["target_year"].between(1946, 2025)
    analysis.loc[target_mask, "conflict_active_t1"] = analysis.loc[
        target_mask, "conflict_active_t1"
    ].fillna(0)
    analysis.loc[target_mask, "conflict_active_t1"] = analysis.loc[
        target_mask, "conflict_active_t1"
    ].astype(int)

    analysis = add_text_features(analysis)

    coverage = (
        analysis.loc[analysis["main_population"]].groupby("year", as_index=False)
        .agg(
            speech_rows=("year", "size"),
            main_population_rows=("main_population", "sum"),
            sipri_observed_rows=("milex_share_gdp_t", "count"),
            conflict_active_rows=("conflict_active_t", lambda values: int((values == 1).sum())),
            next_year_target_rows=("conflict_active_t1", "count"),
        )
    )
    coverage["sipri_observed_rate"] = (
        coverage["sipri_observed_rows"] / coverage["main_population_rows"]
    )
    coverage["conflict_active_rate"] = (
        coverage["conflict_active_rows"] / coverage["main_population_rows"]
    )

    excluded_entities = analysis.loc[
        ~analysis["main_population"],
        ["entity_id", "country_name", "entity_status", "year"],
    ].drop_duplicates()
    missing_sipri = analysis.loc[
        analysis["main_population"] & analysis["milex_share_gdp_t"].isna(),
        ["entity_id", "country_name", "year", "milex_status_t"],
    ]

    audits = {
        **speech_audits,
        "sipri_crosswalk": sipri_crosswalk,
        "ucdp_crosswalk": ucdp_crosswalk,
        "ucdp_excluded_rows": ucdp_exclusions,
        "excluded_speech_entities": excluded_entities,
        "missing_sipri_rows": missing_sipri,
        "coverage_by_year": coverage,
    }
    return PipelineResult(
        analysis=analysis.sort_values(["year", "entity_id"]).reset_index(drop=True),
        speeches=speeches,
        sipri=sipri,
        conflicts=conflicts,
        audits=audits,
    )


def dictionary_context_review(
    analysis: pd.DataFrame,
    examples_per_category_period: int = 4,
    random_state: int = 20260923,
) -> pd.DataFrame:
    records = []
    sentence_split = re.compile(r"(?<=[.!?])\s+")
    periods = pd.cut(
        analysis["year"],
        bins=[1989, 2001, 2013, 2025],
        labels=["1990-2001", "2002-2013", "2014-2025"],
    )
    for category, pattern in DICTIONARY_PATTERNS.items():
        for period in periods.dropna().unique():
            subset = analysis[periods.eq(period)]
            candidates = []
            for row in subset.itertuples():
                for sentence in sentence_split.split(row.speech_clean):
                    match = pattern.search(sentence)
                    if match:
                        candidates.append(
                            {
                                "dictionary": category,
                                "period": str(period),
                                "year": row.year,
                                "entity_id": row.entity_id,
                                "country_name": row.country_name,
                                "matched_term": match.group(0),
                                "context": sentence[:600],
                                "review_decision": "",
                                "review_note": "",
                            }
                        )
            if candidates:
                sample = pd.DataFrame(candidates).sample(
                    n=min(examples_per_category_period, len(candidates)),
                    random_state=random_state,
                )
                records.extend(sample.to_dict("records"))
    return pd.DataFrame(records)


def save_audits(result: PipelineResult, output_dir: Path) -> list[Path]:
    audit_dir = Path(output_dir) / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for name, frame in result.audits.items():
        path = audit_dir / f"{name}.csv"
        frame.to_csv(path, index=False)
        saved.append(path)
    context_path = audit_dir / "dictionary_context_review.csv"
    dictionary_context_review(result.analysis).to_csv(context_path, index=False)
    saved.append(context_path)
    return saved


def save_analysis_table(result: PipelineResult, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "analysis_milestone1.parquet"
    result.analysis.to_parquet(path, index=False)
    return path


def create_initial_eda(result: PipelineResult, output_dir: Path) -> list[Path]:
    output_dir = Path(output_dir) / "eda"
    output_dir.mkdir(parents=True, exist_ok=True)
    data = result.analysis.copy()
    main = data[data["main_population"]].copy()
    saved: list[Path] = []

    coverage = result.audits["coverage_by_year"]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(coverage["year"], 100 * coverage["sipri_observed_rate"], label="SIPRI observed")
    ax.plot(coverage["year"], 100 * coverage["conflict_active_rate"], label="UCDP conflict-active")
    ax.set(
        title="External-data coverage and conflict activity among main-population speeches",
        xlabel="Speech year",
        ylabel="Share of eligible country-year speeches (%)",
        ylim=(0, 100),
    )
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "01_source_coverage_by_year.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    saved.append(path)

    length = main.groupby("year")["speech_token_count"].agg(
        median="median", q25=lambda values: values.quantile(0.25), q75=lambda values: values.quantile(0.75)
    )
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(length.index, length["median"], color="#1f4e79", label="Median")
    ax.fill_between(length.index, length["q25"], length["q75"], color="#9dc3e6", alpha=0.45, label="Middle 50%")
    ax.set(
        title="UN General Debate speech length, 1990-2025",
        xlabel="Speech year",
        ylabel="Cleaned word tokens per speech",
    )
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "02_speech_length_by_year.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    saved.append(path)

    trend_columns = {
        "dict_trust_dialogue_salience_per_1k": "Trust/dialogue salience",
        "dict_cooperation_partnership_per_1k": "Cooperation/partnership",
        "dict_security_threat_salience_per_1k": "Security/threat salience",
        "dict_multilateral_substantive_per_1k": "Substantive multilateralism",
        "dict_transformation_change_per_1k": "Transformation/change",
    }
    # Session 80 transcripts contain unresolved chair/transcriber text.  Keep
    # 2025 in coverage summaries but exclude it from substantive language trends
    # until the manual boundary review is complete.
    trends = main[main["year"].le(2024)].groupby("year")[list(trend_columns)].mean()
    fig, ax = plt.subplots(figsize=(10, 5.8))
    for column, label in trend_columns.items():
        ax.plot(trends.index, trends[column].rolling(3, center=True, min_periods=1).mean(), label=label)
    ax.set(
        title="Average dictionary mentions in UN speeches, 1990-2024 (three-year moving average)",
        xlabel="Speech year",
        ylabel="Mentions per 1,000 cleaned word tokens",
    )
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = output_dir / "03_dictionary_trends.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    saved.append(path)

    predictive = main[main["conflict_active_t1"].notna()].copy()
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))
    plot_categories = [
        ("dict_cooperation_partnership_per_1k", "Cooperation/partnership"),
        ("dict_security_threat_salience_per_1k", "Security/threat salience"),
    ]
    for ax, (column, label) in zip(axes, plot_categories):
        peaceful = predictive.loc[predictive["conflict_active_t1"].eq(0), column]
        conflict = predictive.loc[predictive["conflict_active_t1"].eq(1), column]
        ax.boxplot(
            [peaceful, conflict],
            tick_labels=[f"No conflict\n(n={len(peaceful):,})", f"Conflict\n(n={len(conflict):,})"],
            showfliers=False,
        )
        ax.set(title=label, ylabel="Mentions per 1,000 tokens", xlabel="UCDP status in year t+1")
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Speech-language salience by next-year conflict status (descriptive only)")
    fig.tight_layout()
    path = output_dir / "04_language_by_next_year_conflict.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    saved.append(path)

    return saved
