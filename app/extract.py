"""Extrai arquivos para o estado local, sem gravar tabelas analíticas ou buckets."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from app.rules import sha256
from app.source import read_source


def extract(source, state):
    source, state = Path(source), Path(state)
    # Lê e valida a origem; os hashes identificam de forma estável o conteúdo do lote.
    rows, hashes = read_source(source)
    batch_id = sha256(json.dumps(hashes, sort_keys=True).encode())
    parent = state / "extracted"
    parent.mkdir(parents=True, exist_ok=True)
    final = parent / batch_id
    if not final.exists():
        # Copia primeiro para uma área temporária para não expor um lote incompleto.
        temp = Path(tempfile.mkdtemp(prefix=".staging-", dir=parent))
        try:
            for relative in hashes:
                dst = temp / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, dst)
                # Detecta alterações na origem ocorridas durante a cópia.
                if sha256(dst.read_bytes()) != hashes[relative]:
                    raise ValueError("Source changed during extraction")

            # Registra os arquivos e a contagem usados para validar etapas posteriores.
            (temp / "manifest.json").write_text(json.dumps({
                "batch_id": batch_id, "files": hashes, "book_count": len(rows)}, indent=2))
            # Publica o lote completo de uma só vez; o nome final é determinado pelo conteúdo.
            os.rename(temp, final)
        finally:
            # Remove a área temporária se a extração falhar antes da publicação.
            if temp.exists():
                shutil.rmtree(temp)

    # Revalida o snapshot, inclusive em reexecuções, para não reutilizar arquivos corrompidos.
    for relative, digest in hashes.items():
        if sha256((final / relative).read_bytes()) != digest:
            raise ValueError("Extracted snapshot was modified")

    # Atualiza o ponteiro do lote atual por substituição, evitando expor um JSON parcial.
    state.mkdir(parents=True, exist_ok=True)
    pointer = state / "current.json.tmp"
    pointer.write_text(json.dumps({"batch_id": batch_id, "path": str(final)}))
    pointer.replace(state / "current.json")
    return final


def main():
    p = argparse.ArgumentParser()
    # Permite configurar os diretórios por argumentos ou variáveis de ambiente.
    p.add_argument("--source", default=os.environ.get("SOURCE_DIR", "/opt/lab/data/source"))
    p.add_argument("--state", default=os.environ.get("STATE_DIR", "/opt/lab-state"))
    args = p.parse_args()
    # Executa a extração e informa o caminho do snapshot criado ou reutilizado.
    print(json.dumps({"extracted": str(extract(args.source, args.state))}))


if __name__ == "__main__":
    # Executa a interface de linha de comando quando este módulo é chamado diretamente.
    main()
