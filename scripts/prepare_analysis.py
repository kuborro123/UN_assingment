"""Rebuild the analytical foundation from configurable local source files."""
from pathlib import Path
import sys
import hashlib
import json
import platform
import importlib.metadata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis_pipeline import ProjectPaths, build_analysis, save_audits, create_initial_eda


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(paths=None):
    paths = paths or ProjectPaths.from_env()
    result = build_analysis(paths)
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    save_audits(result, paths.output_dir)
    create_initial_eda(result, paths.output_dir)
    result.analysis.to_parquet(paths.output_dir / "prepared.parquet", index=False)
    result.conflicts.to_parquet(paths.output_dir / "ucdp_country_year.parquet", index=False)
    manifest = {
        "source_hashes": {str(p): sha256(p) for p in
            [paths.metadata_path, paths.conflicts_path, paths.sipri_path]},
        "speech_directory": str(paths.speech_dir),
        "scoped_speech_hash": hashlib.sha256("".join(
            result.analysis.speech_raw.map(lambda x: hashlib.sha256(x.encode()).hexdigest())
        ).encode()).hexdigest(),
        "config_hashes": {p.name: sha256(p) for p in sorted((paths.root / "config").glob("*.csv"))},
        "python": platform.python_version(),
        "packages": {p: importlib.metadata.version(p) for p in
            ["pandas", "numpy", "pyarrow", "openpyxl", "pycountry"]},
        "rows": len(result.analysis), "main_rows": int(result.analysis.main_population.sum()),
        "source_commit": "f44ce6f3cdaf9f252706a86e13a760e90d3824ec",
    }
    (paths.output_dir / "preparation_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2), flush=True)
    return result


def main():
    prepare()


if __name__ == "__main__":
    main()
