import csv
import json
from pathlib import Path
from app.rules import sha256

COLUMNS = ["book_id", "title", "author", "language", "text_file", "text_source"]


def read_source(source, check_manifest=True):
    source = Path(source)
    with (source / "books.csv").open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"Expected CSV columns {COLUMNS}")
        rows = list(reader)
    if not rows:
        raise ValueError("Empty source CSV")
    ids, files = set(), set()
    for row in rows:
        if any(not str(row[c] or "").strip() for c in COLUMNS):
            raise ValueError("Required source field is empty")
        book_id = int(row["book_id"])
        if book_id <= 0 or book_id in ids:
            raise ValueError("book_id must be positive and unique")
        name = row["text_file"]
        if Path(name).name != name or name in files or not name.endswith(".txt"):
            raise ValueError("text_file must be a unique local .txt filename")
        ids.add(book_id)
        files.add(name)
    actual_files = {p.name for p in (source / "texts").glob("*.txt")}
    if actual_files != files:
        raise ValueError("CSV/document set mismatch")
    paths = ["books.csv"] + ["texts/" + name for name in sorted(files)]
    hashes = {name: sha256((source / name).read_bytes()) for name in paths}
    if check_manifest:
        expected = json.loads((source / "SHA256SUMS.json").read_text())
        if hashes != expected:
            raise ValueError("Source checksum mismatch; restore original source or refresh its manifest")
    for name in files:
        (source / "texts" / name).read_bytes().decode("utf-8")
    return rows, hashes
