"""Measure what reaches a model, using the reference implementation.

The default run makes no network connections. `--download` lets tiktoken fetch
its public vocabulary files once into build/tiktoken; no model is called.
Counts from these tokenizers are proxies: the tokenizers of most commercial
models are not public, and counts for them will differ.
"""
import argparse
import csv
import gzip
import io
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(ROOT / "build" / "tiktoken"))

from addp.discovery import Handles, Index, decision_view  # noqa: E402
from addp.protocol import timestamp, Validator  # noqa: E402

AT = "2030-01-01T00:00:00Z"
TOKENIZERS = ("cl100k_base", "o200k_base")
# Flattened candidate columns: (column, path, type). Types let CSV round-trip.
COLUMNS = [
    ("publisher", ("ref", "publisher"), str), ("namespace", ("ref", "namespace"), str),
    ("id", ("ref", "id"), str), ("type", ("type",), str), ("profile", ("profile",), str),
    ("source_revision", ("source_revision",), str), ("retrieved_at", ("retrieved_at",), str),
    ("indexed_at", ("indexed_at",), str), ("valid_until", ("valid_until",), str),
    ("paid_inclusion", ("paid_inclusion",), str), ("name", ("facts", "name"), str),
    ("unit_price_minor", ("facts", "unit_price_minor"), int), ("currency", ("facts", "currency"), str),
    ("condition", ("facts", "condition"), str), ("colour", ("facts", "colour"), str),
    ("availability", ("facts", "availability"), str),
]


def resources():
    for i in range(1, 21):
        publisher = f"https://shop{i}.example"
        yield publisher, {
            "version": "0.1",
            "ref": {"publisher": publisher, "namespace": "addp", "id": publisher + "/addp/resources/offer-17"},
            "type": "https://schema.org/Offer", "profile": "offer-search/0.1", "revision": f"r{i}",
            "facts": {"name": "Sony WH-1000XM6", "unit_price_minor": 29900 + i * 175, "currency": "EUR",
                      "condition": "used" if i % 5 == 0 else "new",
                      "colour": "silver" if i % 4 == 0 else "black", "availability": "in_stock"},
            "capabilities": [], "valid_until": None,
        }


def build(validator):
    now = timestamp(AT)
    index = Index(validator, clock=lambda: now)
    for publisher, resource in resources():
        part_url = publisher + "/addp/feed/s1/1"
        head = {"version": "0.1", "epoch": "e1",
                "snapshot": {"id": "s1", "through": 1, "parts": [part_url], "expires_at": "2030-01-02T00:00:00Z"}}
        part = {"version": "0.1", "epoch": "e1", "snapshot_id": "s1", "through": 1, "resources": [resource]}
        index.install(publisher, head, {part_url: part}, AT)
    query = {"version": "0.1", "profile": "offer-search/0.1", "text": {"mode": "lexical", "value": "Sony WH-1000XM6"},
             "where": [{"field": "currency", "op": "eq", "value": "EUR"},
                       {"field": "condition", "op": "eq", "value": "new"}],
             "select": ["name", "unit_price_minor", "currency", "condition", "colour", "availability"], "limit": 100}
    result = index.query(query)
    result["snapshot"] = "Qm7cX2pL9aR4tZ0e"  # Random in practice; fixed here so counts repeat.
    # Runtime work outside the model: local colour filter, deterministic price ranking.
    eligible = [c for c in result["items"] if c["facts"].get("colour") == "black"]
    top = sorted(eligible, key=lambda c: (c["facts"]["unit_price_minor"], c["ref"]["id"]))[:3]
    handles = Handles(clock=lambda: now)
    handles.scope = "a1b2"
    view = decision_view(top, handles, {"index-A": "ok"}, unresolved=["max_total"])
    return query, result, view


def to_csv(items):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow([c for c, _, _ in COLUMNS])
    for item in items:
        row = []
        for _, path, _ in COLUMNS:
            value = item
            for key in path:
                value = value[key]
            row.append("" if value is None else value)
        writer.writerow(row)
    return stream.getvalue()


def from_csv(text):
    items = []
    for row in csv.DictReader(io.StringIO(text)):
        item = {"ref": {}, "facts": {}}
        for column, path, kind in COLUMNS:
            raw = row[column]
            value = None if raw == "" else kind(raw)
            target = item
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        items.append(item)
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="allow fetching public tokenizer vocabularies")
    args = parser.parse_args()
    if not args.download:
        def offline(*_args, **_kwargs):
            raise RuntimeError("Network disabled; run once with --download")
        socket.socket.connect = offline
        socket.create_connection = offline

    validator = Validator()
    query, result, view = build(validator)
    validator.check("result", result)
    csv_text = to_csv(result["items"])
    assert from_csv(csv_text) == result["items"]  # Same data, not a lossy summary.
    assert all(row["delivered_total"] == "unknown" for row in view["items"])
    assert view["unresolved"] == ["max_total"] and len(view["items"]) == 3

    compact = lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    payloads = {
        "result_json_pretty": json.dumps(result, ensure_ascii=False, indent=2),
        "result_json_compact": compact(result),
        "result_csv_same_data": csv_text,
        "decision_view_json_compact": compact(view),
    }
    measurements = {}
    for name, text in payloads.items():
        data = text.encode("utf-8")
        measurements[name] = {"utf8_bytes": len(data), "gzip_bytes": len(gzip.compress(data, mtime=0)), "tokens": {}}
    tokenizers = {}
    for encoding_name in TOKENIZERS:
        try:
            import tiktoken
            encoding = tiktoken.get_encoding(encoding_name)
        except Exception as exc:  # Missing package or vocabulary.
            tokenizers[encoding_name] = f"unavailable: {type(exc).__name__}"
            continue
        tokenizers[encoding_name] = "proxy tokenizer; not the tokenizer of any particular target model"
        for name, text in payloads.items():
            measurements[name]["tokens"][encoding_name] = len(encoding.encode(text))

    report = {
        "scenario": "20 synthetic offers across 20 publishers; task: three cheapest new black offers",
        "result_items": len(result["items"]), "view_items": len(view["items"]),
        "tokenizers": tokenizers, "measurements": measurements,
    }
    (ROOT / "examples").mkdir(exist_ok=True)
    (ROOT / "examples/context-budget.json").write_text(
        json.dumps({"query": query, "result": result, "decision_view": view}, indent=2) + "\n", encoding="utf-8", newline="\n")
    (ROOT / "docs/measurements.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
