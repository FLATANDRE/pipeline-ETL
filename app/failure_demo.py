"""Teste negativo: marcadores literários inválidos não devem alterar o snapshot de destino."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from app.rules import sha256
from app.trino_client import query


def snapshot():
    # Obtém o snapshot mais recente da tabela para comparar antes e depois do teste.
    result = query('SELECT snapshot_id FROM lake.etl."book_features$snapshots" ORDER BY committed_at DESC LIMIT 1')
    if len(result) != 1:
        raise RuntimeError("Run the healthy pipeline before the negative test")
    return result[0]["snapshot_id"]


def main():
    # Guarda o estado inicial da tabela para comprovar que a carga inválida não foi publicada.
    before = snapshot()
    state = Path(os.environ.get("STATE_DIR", "/opt/lab-state"))

    # Usa uma cópia temporária dos dados para não modificar os arquivos originais.
    with tempfile.TemporaryDirectory(prefix="failure-demo-", dir=state) as temp:
        temp = Path(temp)
        source = temp / "source"
        shutil.copytree(os.environ.get("SOURCE_DIR", "/opt/lab/data/source"), source)

        # Corrompe intencionalmente o marcador inicial de um documento de teste.
        document = source / "texts/pg11.txt"
        data = document.read_bytes()
        if b"*** START OF" not in data:
            raise RuntimeError("Expected marker is absent from fixture")
        document.write_bytes(data.replace(b"*** START OF", b"*** INVALID OF", 1))

        # Atualiza os hashes da cópia para que a extração aceite o fixture modificado.
        hashes = {str(p.relative_to(source)): sha256(p.read_bytes())
                  for p in sorted(source.rglob("*")) if p.is_file() and p.name != "SHA256SUMS.json"}
        (source / "SHA256SUMS.json").write_text(json.dumps(hashes))

        # Executa extração e transformação em diretório de estado isolado.
        env = dict(os.environ, SOURCE_DIR=str(source), STATE_DIR=str(temp / "state"))
        subprocess.run([sys.executable, "-m", "app.extract"], env=env, check=True)
        result = subprocess.run([sys.executable, "-m", "app.transform_load"], env=env, text=True, capture_output=True)
        output = result.stdout + result.stderr

        # Exige que a transformação falhe especificamente pela ausência dos marcadores válidos.
        if result.returncode == 0 or "START/END markers missing or empty: load blocked" not in output:
            print(output)
            raise AssertionError("Expected a controlled validation failure; got a different outcome")

        # Confirma que a falha controlada preservou o snapshot original da tabela.
        after = snapshot()
        if after != before:
            raise AssertionError("Invalid source changed the destination snapshot")
        print(json.dumps({"status": "PASS", "expected_failure": "invalid markers", "snapshot_unchanged": before}))


if __name__ == "__main__":
    # Permite executar o cenário negativo diretamente pela linha de comando.
    main()
