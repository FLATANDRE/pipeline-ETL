import csv
import json
from pathlib import Path
import shutil
import pytest
import yaml
from app.extract import extract
from app.rules import features, sha256
from app.source import COLUMNS, read_source

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/source"


def test_original_hashes():
    rows, hashes = read_source(SOURCE)
    assert len(rows) == 2
    assert len(hashes) == 3


def test_features_match_real_source():
    for row in json.loads((ROOT / "data/expected/features.json").read_text()):
        actual = features((SOURCE / f"texts/pg{row['book_id']}.txt").read_bytes().decode("utf-8"))
        assert actual == {k: row[k] for k in actual}


def test_minimal_text_rule():
    result = features("header *** START OF X *** Alice, ALICE! monster. *** END OF X *** footer")
    assert result["word_count"] == 3
    assert result["alice_mentions"] == 2
    assert result["monster_mentions"] == 1


@pytest.mark.parametrize("text", ["no markers", "*** START OF X ***   *** END OF X ***"])
def test_invalid_markers(text):
    with pytest.raises(ValueError):
        features(text)


def test_extract_snapshot_and_retry(tmp_path):
    first = extract(SOURCE, tmp_path)
    second = extract(SOURCE, tmp_path)
    assert first == second
    assert len(list((tmp_path / "extracted").iterdir())) == 1
    for name, digest in json.loads((first / "manifest.json").read_text())["files"].items():
        assert sha256((first / name).read_bytes()) == digest


def test_corrupted_extract_blocks_reuse(tmp_path):
    path = extract(SOURCE, tmp_path)
    (path / "texts/pg11.txt").write_text("corrupt")
    with pytest.raises(ValueError, match="modified"):
        extract(SOURCE, tmp_path)


def test_bad_checksum_blocks_extract(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    (source / "texts/pg11.txt").write_text("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        extract(source, tmp_path / "state")
    assert not (tmp_path / "state/current.json").exists()


@pytest.mark.parametrize("change", ["duplicate", "empty", "path"])
def test_invalid_metadata(tmp_path, change):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    with (source / "books.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    if change == "duplicate":
        rows[1]["book_id"] = rows[0]["book_id"]
    elif change == "empty":
        rows[0]["title"] = ""
    else:
        rows[0]["text_file"] = "../pg11.txt"
    with (source / "books.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        read_source(source, check_manifest=False)


def test_missing_document(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(SOURCE, source)
    (source / "texts/pg11.txt").unlink()
    with pytest.raises(ValueError, match="set mismatch"):
        read_source(source)


def test_compose_has_no_broker_or_stream_dependencies():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    assert set(compose["services"]) == {"silo", "polaris-db", "polaris-bootstrap", "polaris", "lab-init", "airflow-db", "airflow", "trino"}
    for path in [ROOT / "compose.yaml", ROOT / "docker/Dockerfile", *list((ROOT / "app").glob("*.py")), *list((ROOT / "dags").glob("*.py"))]:
        text = path.read_text().lower()
        assert 'kafka:' not in text
        assert 'spark-sql-kafka' not in text
        assert 'confluent' not in text


def test_destination_write_follows_validation():
    source = (ROOT / "app/transform_load.py").read_text()
    assert source.index('raise ValueError("Feature validation failed') < source.index('.createOrReplace()')
