"""Checkpointed full-corpus scoring. No target/outcome values are loaded."""
from pathlib import Path
import sys
import argparse
import json
import time
import os
import fcntl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from rhetoric_scoring import WholeSpeechScorer, open_cache, text_hash, read_cache, validate_scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("outputs/prepared.parquet"))
    parser.add_argument("--cache", type=Path, default=Path("outputs/rhetoric_full.sqlite"))
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--speech-batch", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None, help="Benchmark only; never treated as a complete cache")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    # OS releases the lock after process exit, including interruption/crashes.
    lock = args.cache.with_suffix(".lock").open("a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("This score cache already has a running writer")
    frame = pd.read_parquet(args.input, columns=["entity_id", "year", "speech_clean"])
    frame = frame.sort_values(["year", "entity_id"]).reset_index(drop=True)
    scorer = WholeSpeechScorer(args.device, args.batch_size)
    db, manifest = open_cache(args.cache, scorer.runtime)
    existing = {(e, y): h for e, y, h in db.execute("SELECT entity_id, year, text_hash FROM scores")}
    pending = []
    for row in frame.itertuples(index=False):
        stored = existing.get((row.entity_id, row.year))
        if stored is not None and stored != text_hash(row.speech_clean):
            raise ValueError(f"Stale cache for {row.entity_id}/{row.year}; use a new cache")
        if stored is None:
            pending.append(row)
    if args.limit is not None:
        pending = pending[:args.limit]
    print(json.dumps(manifest, indent=2), flush=True)
    started, completed = time.monotonic(), 0
    progress_path = args.cache.with_suffix(".progress.json")
    for start in range(0, len(pending), args.speech_batch):
        records = scorer.score_batch(pending[start:start+args.speech_batch])
        with db:
            for record in records:
                db.execute("INSERT INTO scores VALUES (?, ?, ?, ?)",
                    (record["entity_id"], record["year"], record["text_hash"], json.dumps(record)))
        completed += len(records)
        elapsed = time.monotonic() - started
        progress_path.write_text(json.dumps({
            "pid": os.getpid(), "status": "running", "new_completed": completed,
            "cached": len(existing)+completed, "expected": len(frame),
            "elapsed_seconds": elapsed, "seconds_per_speech": elapsed/max(completed,1),
            "updated_unix": time.time(), "cache": str(args.cache.resolve())
        }, indent=2))
        print(f"{completed}/{len(pending)} new speeches; {len(existing)+completed}/{len(frame)} total; "
              f"{elapsed:.1f}s elapsed; {elapsed/max(completed,1):.2f}s/speech", flush=True)
    db.close()
    result = read_cache(args.cache)
    validate_scores(frame, result, require_complete=args.limit is None)
    if args.limit is None:
        result.drop(columns="chunks").to_csv(args.cache.with_suffix(".csv"), index=False)
    print(f"Verified {len(result)} cached speeches", flush=True)
    progress_path.write_text(json.dumps({
        "pid": os.getpid(), "status": "benchmark_complete" if args.limit is not None else "complete",
        "cached": len(result), "expected": len(frame), "updated_unix": time.time(),
        "elapsed_seconds": time.monotonic()-started, "cache": str(args.cache.resolve())
    }, indent=2))


if __name__ == "__main__":
    main()
