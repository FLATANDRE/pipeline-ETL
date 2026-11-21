"""Optional real Spark+Iceberg test on local disk; NOT a Polaris/SILO/Trino test."""
import json
import os
from pathlib import Path
import tempfile
import shutil
from app.extract import extract
from app import transform_load


def main():
    from pyspark.sql import SparkSession
    root = Path(__file__).resolve().parents[1]
    runtime = os.environ["ICEBERG_RUNTIME_JAR"]
    with tempfile.TemporaryDirectory(prefix="etl-spark-test-") as temp:
        temp = Path(temp)
        warehouse = (temp / "warehouse").as_uri()
        def session():
            spark = (SparkSession.builder.master("local[2]").appName("local-etl-verification")
                .config("spark.jars", runtime)
                .config("spark.ui.enabled", "false")
                .config("spark.driver.host", "127.0.0.1")
                .config("spark.driver.bindAddress", "127.0.0.1")
                .config("spark.sql.shuffle.partitions", "2")
                .config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog")
                .config("spark.sql.catalog.lake.type", "hadoop")
                .config("spark.sql.catalog.lake.warehouse", warehouse)
                .getOrCreate())
            spark.sparkContext.setLogLevel("ERROR")
            return spark
        os.environ["STATE_DIR"] = str(temp / "state")
        extract(root / "data/source", temp / "state")
        transform_load.spark_session = session
        expected = json.loads((root / "data/expected/features.json").read_text())
        counts = []
        for _ in range(2):
            transform_load.main()
            spark = session()
            try:
                cols = ["book_id", "body_char_count", "word_count", "alice_mentions", "monster_mentions"]
                result = [r.asDict() for r in spark.table("lake.etl.book_features").select(*cols).orderBy("book_id").collect()]
                assert result == expected
                counts.append(spark.table("lake.etl.book_features").count())
            finally:
                spark.stop()
        spark = session()
        before = spark.sql('SELECT snapshot_id FROM lake.etl.book_features.snapshots ORDER BY committed_at DESC LIMIT 1').first()[0]
        spark.stop()
        bad_source = temp / "bad-source"
        shutil.copytree(root / "data/source", bad_source)
        document = bad_source / "texts/pg11.txt"
        document.write_bytes(document.read_bytes().replace(b"*** START OF", b"*** INVALID OF", 1))
        from app.rules import sha256
        hashes = {str(p.relative_to(bad_source)): sha256(p.read_bytes()) for p in sorted(bad_source.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.json"}
        (bad_source / "SHA256SUMS.json").write_text(json.dumps(hashes))
        os.environ["STATE_DIR"] = str(temp / "bad-state")
        extract(bad_source, temp / "bad-state")
        try:
            transform_load.main()
        except ValueError as exc:
            assert "START/END markers missing or empty" in str(exc)
        else:
            raise AssertionError("Expected controlled transformation failure")
        spark = session()
        try:
            after = spark.sql('SELECT snapshot_id FROM lake.etl.book_features.snapshots ORDER BY committed_at DESC LIMIT 1').first()[0]
            assert after == before
        finally:
            spark.stop()
        print(json.dumps({"status": "PASS", "negative_test": "invalid markers blocked; snapshot unchanged", "spark": "3.5.7", "iceberg": "1.10.0", "backend": "local HadoopCatalog", "row_counts_after_two_runs": counts}))


if __name__ == "__main__":
    main()
