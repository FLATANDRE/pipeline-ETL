import json
import os
from pathlib import Path
from app.settings import settings
from app.trino_client import query


def main():
    # Carrega os resultados de referência e define as métricas que serão comparadas.
    expected = json.loads(Path("/opt/lab/data/expected/features.json").read_text())
    columns = ["book_id", "body_char_count", "word_count", "alice_mentions", "monster_mentions"]

    # Consulta a tabela de destino em ordem estável para comparar com os valores esperados.
    actual = query("SELECT " + ", ".join(columns) + " FROM " + settings()["table"] + " ORDER BY book_id")
    if actual != expected:
        raise AssertionError(json.dumps({"expected": expected, "actual": actual}))

    # Confere se a tabela contém dados do mesmo lote de origem extraído mais recentemente.
    state = Path(os.environ.get("STATE_DIR", "/opt/lab-state"))
    batch_id = json.loads((state / "current.json").read_text())["batch_id"]
    batches = query("SELECT DISTINCT source_batch_id FROM " + settings()["table"])
    if batches != [{"source_batch_id": batch_id}]:
        raise AssertionError("Destination batch does not match latest extracted source")

    # Registra e imprime o relatório quando as verificações de conteúdo e linhagem passam.
    report = {"status": "PASS", "table": settings()["table"], "rows": actual, "batch_id": batch_id}
    (state / "validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    # Executa as verificações ao iniciar o módulo diretamente.
    main()
