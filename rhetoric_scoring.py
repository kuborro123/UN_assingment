"""Whole-speech local theme compatibility; no outcome data enter inference."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

SPEC = {
    "version": "whole-speech-v2",
    "pair_format": "[CLS] premise [SEP] hypothesis [SEP]",
    "model": "MoritzLaurer/ModernBERT-large-zeroshot-v2.0",
    "revision": "a51e07b524299e309dd2b88d48b0cfa2bd9ec598",
    "labels": ["trust and international cooperation", "military threat and security concerns"],
    "template": "This example is {}.",
    "multi_label": True,
    "max_premise_tokens": 480,
    "max_pair_tokens": 512,
    "chunk_boundary": "sentence ending in latter half of window, else token boundary",
    "aggregation": "premise-token-weighted arithmetic mean",
    "overlap": 0,
    "dtype": "float32",
    "seed": 20260925,
}
SPEC_HASH = hashlib.sha256(json.dumps(SPEC, sort_keys=True).encode()).hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_tokens(text, tokenizer, budget=480):
    """Partition original token IDs, avoiding decode/re-encode token loss."""
    if budget < 2:
        raise ValueError("Token budget must be at least two")
    encoded = tokenizer(text, add_special_tokens=False, truncation=False,
                        return_offsets_mapping=True, verbose=False)
    ids, offsets = encoded["input_ids"], encoded["offset_mapping"]
    if not ids:
        raise ValueError("Empty speech")
    sentence_ends = {m.end() for m in re.finditer(r'[.!?](?:["”’\x27])?(?=\s|$)', text)}
    # Token end offsets, not re-tokenized sentence strings, define boundaries.
    boundaries = [i + 1 for i, (_, end) in enumerate(offsets) if end in sentence_ends]
    chunks = []
    start = 0
    while start < len(ids):
        end = min(start + budget, len(ids))
        if end < len(ids):
            candidates = [b for b in boundaries if start + budget // 2 <= b <= end]
            if candidates:
                end = candidates[-1]
        chunks.append({"ids": ids[start:end], "start_token": start, "end_token": end,
                       "start_char": offsets[start][0], "end_char": offsets[end - 1][1]})
        start = end
    assert sum(len(c["ids"]) for c in chunks) == len(ids)
    assert [v for c in chunks for v in c["ids"]] == ids
    return chunks


def aggregate_scores(scores, token_counts):
    scores, weights = np.asarray(scores, dtype=float), np.asarray(token_counts, dtype=float)
    if scores.shape != (len(weights), 2) or np.any(weights <= 0):
        raise ValueError("Expected two independent scores per non-empty chunk")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Scores must be finite in [0, 1]")
    return np.average(scores, axis=0, weights=weights)


def make_model_pair(premise_ids, hypothesis_ids, tokenizer):
    """Apply the pinned fast-tokenizer pair template without re-tokenizing chunks.

    Generic prepare_for_model on this PreTrainedTokenizerFast does NOT apply its
    backend post-processor. Omitting CLS/SEP silently changes model predictions.
    The scorer checks this explicit template against normal paired tokenization.
    """
    if tokenizer.cls_token_id is None or tokenizer.sep_token_id is None:
        raise ValueError("Checkpoint lacks required CLS/SEP tokens")
    ids = ([tokenizer.cls_token_id] + list(premise_ids) + [tokenizer.sep_token_id]
           + list(hypothesis_ids) + [tokenizer.sep_token_id])
    if len(ids) > SPEC["max_pair_tokens"]:
        raise ValueError("Chunk plus hypothesis exceeds verified token limit")
    return {"input_ids": ids, "attention_mask": [1] * len(ids)}


def open_cache(path, runtime):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute("""CREATE TABLE IF NOT EXISTS scores (
        entity_id TEXT, year INTEGER, text_hash TEXT, payload TEXT NOT NULL,
        PRIMARY KEY (entity_id, year))""")
    manifest = {"spec": SPEC, "spec_hash": SPEC_HASH, "runtime": runtime}
    value = json.dumps(manifest, sort_keys=True)
    existing = db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()
    if existing and existing[0] != value:
        db.close()
        raise ValueError("Cache specification/runtime differs; use a new cache path")
    db.execute("INSERT OR IGNORE INTO metadata VALUES ('manifest', ?)", (value,))
    db.commit()
    return db, manifest


def validate_scores(frame, scores, require_complete=True):
    """Reject stale texts, missing chunks, mismatched specifications or duplicate keys."""
    key = ["entity_id", "year"]
    if frame.duplicated(key).any() or scores.duplicated(key).any():
        raise ValueError("Duplicate score/input entity-year keys")
    expected = frame[key].copy()
    expected["expected_hash"] = frame.speech_clean.map(text_hash)
    joined = expected.merge(scores, on=key, how="left", validate="one_to_one")
    missing = joined.text_hash.isna()
    if require_complete and missing.any():
        raise ValueError(f"Missing scores for {int(missing.sum())} speeches")
    present = joined.loc[~missing]
    if not present.expected_hash.eq(present.text_hash).all():
        raise ValueError("Stale scores: cleaned text hash changed")
    if not present.spec_hash.eq(SPEC_HASH).all():
        raise ValueError("Wrong scoring specification")
    if not present.token_coverage.eq(1).all():
        raise ValueError("Incomplete token coverage")
    if not present.tokens_scored.eq(present.model_token_count).all():
        raise ValueError("Scored token count differs from full speech")
    for c in ["trust_score", "threat_score"]:
        if not present[c].between(0, 1).all():
            raise ValueError("Invalid rhetoric score")
    return joined.drop(columns="expected_hash")


class WholeSpeechScorer:
    def __init__(self, device="auto", batch_size=8):
        import torch
        import transformers
        import tokenizers
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        torch.manual_seed(SPEC["seed"])
        np.random.seed(SPEC["seed"])
        if device == "auto":
            device = "mps" if torch.backends.mps.is_available() else (
                "cuda" if torch.cuda.is_available() else "cpu")
        self.torch, self.device, self.batch_size = torch, device, batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(SPEC["model"], revision=SPEC["revision"])
        for premise in ["Hello world.", "We do not support war; Côte d’Ivoire speaks."]:
            hypothesis = SPEC["template"].format(SPEC["labels"][0])
            expected = self.tokenizer(premise, hypothesis, truncation=False)
            actual = make_model_pair(
                self.tokenizer(premise, add_special_tokens=False)["input_ids"],
                self.tokenizer(hypothesis, add_special_tokens=False)["input_ids"], self.tokenizer)
            if actual != dict(expected):
                raise ValueError("Explicit pair template differs from pinned tokenizer")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            SPEC["model"], revision=SPEC["revision"], reference_compile=False,
            torch_dtype=torch.float32).to(device).eval()
        if self.model.config.label2id != {"entailment": 0, "not_entailment": 1}:
            raise ValueError("Unexpected checkpoint label mapping")
        self.hypotheses = [self.tokenizer(SPEC["template"].format(label),
                           add_special_tokens=False)["input_ids"] for label in SPEC["labels"]]
        self.runtime = {"torch": torch.__version__, "transformers": transformers.__version__,
                        "tokenizers": tokenizers.__version__, "device": device,
                        "batch_size": batch_size, "reference_compile": False,
                        "tokenizer_sha256": text_hash(self.tokenizer.backend_tokenizer.to_str()),
                        "model_config_sha256": text_hash(self.model.config.to_json_string())}

    def score_batch(self, rows):
        prepared, descriptions = [], []
        for row in rows:
            chunks = chunk_tokens(row.speech_clean, self.tokenizer, SPEC["max_premise_tokens"])
            descriptions.append((row, chunks))
            for chunk in chunks:
                for hypothesis in self.hypotheses:
                    pair = make_model_pair(chunk["ids"], hypothesis, self.tokenizer)
                    if len(pair["input_ids"]) > SPEC["max_pair_tokens"]:
                        raise ValueError("Chunk plus hypothesis exceeds verified token limit")
                    prepared.append(pair)
        probabilities = []
        with self.torch.inference_mode():
            for start in range(0, len(prepared), self.batch_size):
                inputs = self.tokenizer.pad(prepared[start:start+self.batch_size], padding=True,
                                            return_tensors="pt").to(self.device)
                logits = self.model(**inputs).logits
                probabilities.extend(self.torch.softmax(logits.float(), dim=-1)[:, 0].cpu().tolist())
        records, offset = [], 0
        for row, chunks in descriptions:
            n = len(chunks)
            scores = np.asarray(probabilities[offset:offset+2*n]).reshape(n, 2)
            offset += 2*n
            counts = [len(c["ids"]) for c in chunks]
            trust, threat = aggregate_scores(scores, counts)
            records.append({"entity_id": row.entity_id, "year": int(row.year),
                "text_hash": text_hash(row.speech_clean), "spec_hash": SPEC_HASH,
                "trust_score": float(trust), "threat_score": float(threat),
                "model_token_count": sum(counts), "tokens_scored": sum(counts),
                "token_coverage": 1.0, "chunk_count": n,
                "chunk_tokens_min": min(counts), "chunk_tokens_median": float(np.median(counts)),
                "chunk_tokens_max": max(counts),
                "chunks": [{"start_token": c["start_token"], "end_token": c["end_token"],
                    "start_char": c["start_char"], "end_char": c["end_char"],
                    "tokens": counts[i], "trust": float(scores[i, 0]),
                    "threat": float(scores[i, 1])} for i, c in enumerate(chunks)]})
        return records


def read_cache(path):
    if not Path(path).is_file():
        raise FileNotFoundError(f"Run scripts/score_speeches.py first: {path}")
    with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True) as db:
        records = [json.loads(row[0]) for row in db.execute("SELECT payload FROM scores ORDER BY year,entity_id")]
    return pd.DataFrame(records)
