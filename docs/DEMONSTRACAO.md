# Guia de gravação — ETL por arquivos

## Antes de gravar

1. Execute `bash scripts/start.sh` e aguarde a inicialização.
2. Execute `bash scripts/smoke.sh`. Só grave a demonstração se esse teste passar no seu host.
3. Abra Airflow, SILO Console e o terminal Trino. Não grave downloads de imagem ou instalação de pacotes.
4. Evite rodar a DAG e os scripts CLI ao mesmo tempo: compartilham `current.json` e tabela de destino.

## Abertura

> Uma planilha conhece o título do livro. Um TXT conhece a história inteira. Agora vamos transformar essas duas fontes em uma tabela consultável — e conferir por que esse caminho é ETL, sem precisar de um broker de mensagens.

Mostre rapidamente CSV, TXT e a tabela final; volte ao diagrama em `arquitetura.svg`. O arquivo Mermaid permite adaptar a composição.

## Tópicos e demonstração

- **Defina o destino:** lakehouse Iceberg/SILO. A cópia temporária local é a área de extração, não uma camada bronze nesse destino.
- **Mostre `data/source/books.csv` e um TXT:** dados estruturados e não estruturados participam do MESMO pipeline.
- **Abra a DAG `demo_etl_books`:** `extract_files -> transform_then_load -> validate_with_trino`.
- **Mostre `app/extract.py`:** checksums, snapshot local imutável por batch e controle de retry. Nenhum documento bruto é carregado no SILO por esta etapa.
- **Mostre `app/transform_load.py`:** leitura Spark, join, integridade, recorte START/END, tokens e validação. A chamada `createOrReplace()` vem DEPOIS das verificações.
- **Execute pelo Airflow:** observe logs e estados. Airflow coordena; Spark processa. Não mova o conteúdo dos livros por XCom.
- **Consulte a tabela:** use `sql/demo.sql` no Trino. Explique que o resultado não contém o texto original.
- **Abra o SILO:** o bucket `warehouse` contém arquivos de tabela e metadados, não uma coleção de TXT brutos.
- **Explique o catálogo:** Spark e Trino usam o mesmo Polaris; não são duas cópias independentes da tabela.
- **Mostre a falha controlada:** `docker compose exec -T airflow python -m app.failure_demo`. O teste cria uma cópia defeituosa descartável, espera erro específico e verifica que o snapshot de destino não mudou. O resultado PASS significa que a falha esperada foi controlada.
- **Reexecute:** `bash scripts/run.sh` mantém duas linhas na visão atual. Pode haver novo snapshot: idempotência lógica não significa ausência de novos arquivos ou commits.

## Frases de impacto

- A ferramenta não define a sigla; a ordem em relação ao destino define.
- O dado só é publicado depois de passar pelas regras.
- Orquestrar não é processar: cada componente tem uma responsabilidade.
- Pipeline confiável precisa mostrar o que acontece quando o dado está errado.

## Encerramento

> O nosso ETL preparou a informação antes de publicar a tabela no lakehouse. O próximo passo não é escolher uma sigla da moda: é decidir que contrato o destino precisa receber e de onde virá o dado se uma nova regra exigir reprocessamento.

## Não afirmar

- Que ETL elimina qualquer cópia bruta: há arquivos de origem e snapshots locais.
- Que o laboratório é streaming ou CDC: é batch por arquivos.
- Que a extração lexical compreende semanticamente os livros.
- Que o Polaris impede acesso direto de quem possui as chaves administrativas do SILO.
- Que as versões foram homologadas fim a fim neste ambiente: consulte `VALIDATION.json`.
