# Projeto ETL — Airflow, PySpark, Iceberg, SILO, Polaris e Trino

**Projeto completo de demonstração, sem Kafka.** A entrada é feita diretamente por arquivos CSV e TXT incluídos no pacote. Não há broker, tópico, producer, consumer, conector Kafka, ZooKeeper ou dependência de streaming.

## Fluxo

```text
CSV estruturado + TXT não estruturado
                  |
          Extração por arquivos
          Snapshot LOCAL + SHA-256
                  |
        PySpark: validar e transformar
                  |
        Tabela Iceberg no SILO
                  |
            Consulta Trino

Airflow coordena as etapas.
Polaris mantém o catálogo REST usado por Spark e Trino.
```

**Por que é ETL:** o destino analítico de referência é o lakehouse Iceberg/SILO. As características dos documentos são calculadas e verificadas ANTES da primeira escrita da tabela nesse destino. O snapshot local de extração não é uma camada bronze carregada no SILO. Os arquivos brutos continuam existindo na origem e na área de trabalho local.

**Status da validação:** 17 testes unitários/offline passaram; a configuração foi verificada pelo Docker Compose oficial v2.39.4; houve execução REAL com Spark 3.5.7 + Iceberg 1.10.0 e catálogo Hadoop local, incluindo duas cargas com duas linhas finais e falha controlada sem alterar o snapshot anterior. **Não houve execução dos containers nem integração fim a fim Airflow–Polaris–SILO–Trino neste ambiente.** O teste local usa Java 17.0.21; a imagem Docker fixa Java 17.0.17. Consulte `VALIDATION.json`; não confunda os escopos dos testes.

## O exemplo

Uma biblioteca digital com dois documentos reais do Project Gutenberg:

- `data/source/books.csv`: identificador, título, autor, idioma, arquivo e fonte.
- `data/source/texts/pg11.txt`: Alice's Adventures in Wonderland.
- `data/source/texts/pg84.txt`: Frankenstein.

O pipeline relaciona os metadados aos textos e calcula métricas lexicais simples. Não é um modelo de IA, não contém dados pessoais nem simulação de faturamento. Fontes, avisos de direitos e definição dos tokens estão em `data/README.md`.

| Livro | Tokens `[a-z]+` | Token `alice` | Token `monster` |
|---|---:|---:|---:|
| Alice's Adventures in Wonderland | 27.427 | 399 | 0 |
| Frankenstein | 75.328 | 0 | 31 |

As contagens dependem da regra e da edição incluída. Os hashes detectam alterações nos dados; não baixe outra edição e espere as mesmas contagens. O marcador START/END delimita o corpo, que ainda pode incluir títulos e notas.

## Pré-requisitos

- Docker Engine ou Docker Desktop com Compose v2.39.4 ou compatível; WSL2 recomendado no Windows.
- Sugestão operacional, NÃO um requisito mínimo medido: 4 CPUs, 12–16 GB de RAM disponíveis ao Docker e 15 GB de disco para imagens/builds.
- Internet para baixar imagens, pacotes e JARs no primeiro build. Os dados do exemplo já estão incluídos.
- Portas livres: 8080, 8081, 8181, 8182, 9000, 9001; 8501 para o dashboard opcional.
- Evite executar outra stack com as mesmas portas.

## Inicialização rápida

Descompacte e abra o terminal na raiz que contém `compose.yaml`:

```bash
cp .env.example .env
docker compose config --quiet
docker compose build lab-init
docker compose up -d
```

Alternativa Linux/WSL/macOS:

```bash
bash scripts/start.sh
```

O primeiro build é grande: PySpark, Java e dois JARs são baixados. A instalação fixa versões, mas não é um lock transitivo de todas as dependências Python. **Não foi executado `docker build` aqui.** Os JARs têm SHA-512 verificado durante o build. Se mudar `ICEBERG_VERSION`, também atualize os hashes no Dockerfile, em vez de desabilitar a verificação.

Acompanhe a inicialização:

```bash
docker compose ps -a
docker compose logs -f polaris-bootstrap polaris lab-init airflow
```

`polaris-bootstrap` e `lab-init` devem sair com código **0**. São tarefas de inicialização; não precisam permanecer rodando. `lab-init` espera o storage e o OAuth do Polaris, cria bucket, catálogo, role e grant e gera o arquivo de catálogo do Trino. Os bancos de metadados de Airflow e Polaris são separados.

O bootstrap reconhece um metastore Polaris já inicializado em execuções posteriores; nenhum volume ou dado é apagado.

## Interfaces

| Interface | Endereço | Acesso local |
|---|---|---|
| Airflow | http://localhost:8080 | SimpleAuthManager com todos administradores; sem login efetivo |
| SILO Console | http://localhost:9001 | `S3_ACCESS_KEY` e `S3_SECRET_KEY` do `.env` |
| SILO API S3 | http://localhost:9000 | Mesmas chaves; use clientes S3 |
| Trino UI | http://localhost:8081 | Sem autenticação na demo |
| Polaris API | http://localhost:8181 | OAuth configurado pelo bootstrap |
| Polaris health | http://localhost:8182/q/health | Diagnóstico |
| Dashboard (opcional) | http://localhost:8501 | Sem autenticação na demo |

As portas publicadas ficam em `127.0.0.1`. **Não exponha o laboratório à internet.** O Airflow usa `standalone` para reunir os processos necessários em um serviço local, não como topologia de produção.

## Rodar pelo Airflow

1. Aguarde a interface abrir e o scan da DAG terminar.
2. Habilite `demo_etl_books`.
3. Acione uma execução manual.
4. Acompanhe `extract_files -> transform_then_load -> validate_with_trino`.
5. Confira os logs da validação; o resultado esperado é `PASS` e dois livros.

Alternativa para disparar uma execução real da DAG:

```bash
bash scripts/trigger_dag.sh
```

## Rodar por linha de comando

Para rodar os MESMOS módulos da DAG, sem registrar uma execução de DAG:

```bash
bash scripts/run.sh
```

Ou execute individualmente:

```bash
docker compose exec -T airflow python -m app.doctor
docker compose exec -T airflow python -m app.extract
docker compose exec -T airflow python -m app.transform_load
docker compose exec -T airflow python -m app.validate
```

**Não execute a DAG e a alternativa CLI ao mesmo tempo.** Compartilham o apontador de batch e a tabela de saída. `max_active_runs=1` protege as execuções da DAG entre si, não scripts manuais concorrentes.

## Consultar o resultado

```bash
docker compose exec -T trino trino --execute 'SELECT book_id, title, word_count, alice_mentions, monster_mentions FROM lake.etl.book_features ORDER BY book_id'
```

Consultas de rastreabilidade, snapshots e arquivos estão em `sql/demo.sql`. Para listar os objetos no storage:

```bash
docker compose exec -T airflow python -m app.inspect_storage
```

O bucket `warehouse` guarda arquivos Parquet/metadados da tabela. **A extração não sobe TXT brutos para esse bucket.** A tabela final preserva hash e batch de origem, não o conteúdo literário completo.

## Dashboard

Depois de executar o pipeline e criar a tabela, inicie o dashboard opcional:

```bash
docker compose --profile dashboard up -d --build dashboard
```

Abra http://localhost:8501 para explorar os livros, filtrar por autor e idioma e comparar tokens e menções. Os dados vêm de `lake.etl.book_features` pelo Trino; não são carregados das fixtures locais. A consulta é armazenada em cache por até 60 segundos e pode ser atualizada pelo botão lateral. Se a tabela ainda não existir, execute o pipeline e atualize a página. O serviço publica a porta apenas no localhost e não possui autenticação.

## Falha controlada e retry

Depois de uma execução saudável:

```bash
docker compose exec -T airflow python -m app.failure_demo
```

O teste cria uma cópia temporária da origem, invalida o marcador START de um documento, atualiza o manifesto dessa cópia e executa o job contra um estado separado. Espera o erro específico da transformação e compara o snapshot de destino antes/depois. Um `PASS` comprova que, nesse teste local do seu host, a validação barrou a substituição. A origem original não é alterada.

Para testar execução saudável, falha controlada e reexecução:

```bash
bash scripts/smoke.sh
```

Esse smoke test usa os módulos CLI e APIs reais; **não testa o scheduler/worker do Airflow**. Execute também a DAG pela interface para validar a orquestração fim a fim. O smoke test dos containers precisa ser executado no seu host: não foi executado aqui.

Reprocessar o mesmo batch substitui o conteúdo lógico da tabela; não faz append de linhas duplicadas. Pode criar novo snapshot e novos arquivos. Não há garantia de ausência de efeitos físicos em retries; a propriedade demonstrada é repetibilidade da saída lógica.

## Estrutura

```text
compose.yaml                 Serviços e volumes, sem mensageria
.env.example                 Versões e credenciais de laboratório
docker/Dockerfile            Airflow + Java + PySpark + Iceberg/AWS
app/bootstrap.py             Bucket, catálogo, grants e Trino
app/extract.py               Snapshot local por batch e hashes
app/transform_load.py        Transformações Spark e carga Iceberg
app/validate.py              Resultado comparado por Trino
app/doctor.py                Conectividade e catálogo
app/failure_demo.py          Erro controlado sem substituir destino
app/inspect_storage.py       Inspeção do bucket
dags/etl_books.py            DAG com três tasks
dashboard/                   Aplicação Streamlit e sua imagem
config/trino/                Coordenador e JVM
sql/demo.sql                 Consultas de gravação/inspeção
scripts/                     Start, execução, trigger e smoke
data/source/                 CSV e TXT reais incluídos
data/expected/               Resultados da regra distribuída
tests/                       Unitários e teste opcional Spark real
docs/                        Diagrama SVG/Mermaid e guia de gravação
VALIDATION.json              Evidências e limites
```

## Versões fixadas

| Componente | Versão |
|---|---|
| Airflow / Python | 3.3.2 / 3.11 |
| Provider standard Airflow | 1.19.0 |
| PySpark / Scala | 3.5.7 / 2.12 |
| Iceberg Spark runtime e AWS bundle | 1.10.0 |
| Polaris / admin-tool | 1.5.0 |
| SILO | RELEASE.2026-10-26T00-00-00Z |
| Trino | 484 |
| PostgreSQL | 17.6 |
| Java da imagem | Temurin 17.0.17_10 JRE |

São escolhas fixadas para o laboratório, não uma declaração de últimas versões, ausência de CVEs ou suporte de longo prazo. A existência das tags principais foi consultada no registry. Não substitua uma versão isolada sem revisar propriedades, avisos e interoperabilidade.

## Testes offline

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q -p no:cacheprovider
```

Para incluir os testes do dashboard, instale também `dashboard/requirements.txt` no ambiente de testes.

Ou dentro da imagem depois de iniciada:

```bash
docker compose exec -T airflow python -m pytest -q -p no:cacheprovider
```

O teste Spark opcional `tests/spark_local_smoke.py` precisa de Java 17, PySpark 3.5.7 e variável `ICEBERG_RUNTIME_JAR` apontando ao runtime Iceberg 1.10.0. Usa catálogo Hadoop **local apenas para teste**; o projeto entregue usa REST Polaris. Ele exercita a transformação real, duas escritas Iceberg e a preservação do snapshot diante de erro; não comprova integração S3/REST/Trino.

## Segurança e limitações

- Batch completo de arquivos; sem streaming, CDC ou incremental por offsets.
- A extração copia arquivos em volume local `work-data` e faz hashes. Não representa uma origem distribuída em escala. Snapshots locais não são removidos automaticamente.
- Spark roda em `local[2]` no serviço Airflow. É um laboratório, não um cluster Spark nem recomendação de processamento pesado no scheduler de produção.
- Validação de qualidade acontece antes da escrita. `createOrReplace` usa commit de tabela Iceberg; não transforma toda a DAG, o storage e o catálogo numa única transação distribuída.
- O validador final compara a fixture incluída. Ao trocar fontes/regras, atualize hashes e expectativas de forma deliberada.
- Chaves administrativas estáticas, HTTP sem TLS, serviços únicos e autenticação simplificada. Sem HA, backup, SLA, secrets manager ou telemetria operacional completa.
- `stsUnavailable=true` e credential vending desativado são uma escolha de autenticação estática nesta demo; **não significa que o SILO não tenha STS**.
- Polaris governa o catálogo; chaves S3 administrativas permitem acesso direto ao storage. Produção requer identidades separadas, menor privilégio e revisão do acesso físico.
- O catálogo usa as credenciais administrativas do bootstrap também nos clientes por simplificação. Não anunciar isolamento de permissões como demonstrado.
- Arquivos gerados do Trino contêm segredos e são legíveis no volume compartilhado para o usuário do Trino. Restrinja acesso ao host e a esse volume.
- Os snapshots anteriores e arquivos históricos podem consumir espaço. Não há rotina automática de expiração ou garbage collection.
- A stack é propositalmente grande para poucos documentos: não use o tempo ou consumo deste exemplo como benchmark de custos.

## Diagnóstico

| Sintoma | Ação |
|---|---|
| `lab-init` sai com erro | Veja `docker compose logs lab-init polaris`; confira o corpo do erro HTTP |
| `401` no Polaris | Confira realm, client ID/secret e se o banco foi inicializado com esses mesmos valores |
| `403` no Polaris | Confira grant `CATALOG_MANAGE_CONTENT` e associação de `lab_writer` a `service_admin` |
| Erro S3 / AccessDenied | Confira mesmas chaves nos serviços e endpoint interno `http://silo:9000` |
| `localhost` não funciona no Spark | Dentro dos containers storage é `silo`, catálogo é `polaris`, Trino é `trino` |
| Trino não conhece catálogo `lake` | Confira `lab-init` e o volume `generated-config`; reinicie Trino após corrigir a configuração |
| DAG não aparece | Veja `docker compose logs airflow`; aguarde o DAG processor e confira import errors |
| ClassNotFound Iceberg | Refaça `docker compose build --no-cache lab-init`; confirme os dois JARs |
| OOM / exit 137 | Aumente memória do Docker; não execute testes Spark concorrentes |
| Hash divergente | Restaure os arquivos originais; edição/fins de linha alterados mudam o hash |
| Senhas mudadas após primeira inicialização | `.env` não rotaciona automaticamente senhas já persistidas; faça rotação ou reset somente se os dados forem descartáveis |
| Build falha no pip | Capture o erro do resolvedor; não use `--no-deps` para esconder conflitos. Este build não foi homologado aqui |

Para Windows, use terminal WSL2 e execute `bash scripts/...`; no PowerShell, `Copy-Item .env.example .env` substitui `cp`, e os comandos `docker compose` permanecem válidos.

## Parar e resetar

Preservar os dados:

```bash
docker compose stop
```

Remover containers/rede, mantendo volumes:

```bash
docker compose down
```

**DESTRUTIVO: apagar dados, catálogo, snapshots locais e histórico do Airflow:**

```bash
docker compose down -v
```

## Fontes de configuração

- SILO Docker e healthcheck: https://silo.pgsty.com/docs/
- SILO versão fixada: https://silo.pgsty.com/blog/release/silo-20261026/
- Polaris versão fixada: https://polaris.apache.org/releases/1.5.0/
- Contrato REST: https://github.com/apache/polaris/blob/apache-polaris-1.5.0/spec/polaris-management-service.yml
- Polaris JDBC: https://github.com/apache/polaris/blob/apache-polaris-1.5.0/site/content/in-dev/unreleased/metastores/relational-jdbc.md
- Spark/Polaris: https://polaris.apache.org/guides/spark/
- Trino/Polaris: https://polaris.apache.org/guides/trino/
- Airflow SimpleAuthManager (desenvolvimento/testes): https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/auth-manager/simple/index.html

Os links documentam os componentes; não constituem certificação da combinação entregue.
