import json
import os
from pathlib import Path
from app.rules import BODY_PATTERN, TOKEN_PATTERN, sha256
from app.settings import settings
from app.spark_session import spark_session


def main():
    from pyspark.sql import functions as F, types as T

    # Localiza o lote extraído e carrega seus metadados de controle.
    state = Path(os.environ.get("STATE_DIR", "/opt/lab-state"))
    pointer = json.loads((state / "current.json").read_text())
    batch = Path(pointer["path"])
    manifest = json.loads((batch / "manifest.json").read_text())

    # Confere os arquivos do lote antes de iniciar qualquer processamento.
    for relative, digest in manifest["files"].items():
        if sha256((batch / relative).read_bytes()) != digest:
            raise ValueError("Extracted source integrity failure before processing")

    spark = spark_session()
    result = None
    try:
        # Define os tipos das colunas para evitar inferência automática do Spark.
        schema = T.StructType([
            T.StructField("book_id", T.IntegerType()), T.StructField("title", T.StringType()),
            T.StructField("author", T.StringType()), T.StructField("language", T.StringType()),
            T.StructField("text_file", T.StringType()), T.StructField("text_source", T.StringType())])

        # Lê os metadados dos livros e o conteúdo integral de cada arquivo de texto.
        books = spark.read.schema(schema).option("header", "true").option("mode", "FAILFAST").csv(str(batch / "books.csv"))
        pairs = spark.sparkContext.wholeTextFiles(str(batch / "texts" / "*.txt"))
        docs = spark.createDataFrame(pairs.map(lambda p: (p[0].rsplit("/", 1)[-1], p[1])), "text_file string, text string")

        # Prepara os hashes declarados no manifesto para compará-los ao conteúdo lido.
        hashes = [(name.split("/", 1)[1], digest) for name, digest in manifest["files"].items() if name.startswith("texts/")]
        expected_hash = spark.createDataFrame(hashes, "text_file string, content_sha256 string")

        # Garante que não faltam livros ou documentos e que seus identificadores são únicos.
        if books.count() != manifest["book_count"] or books.select("book_id").distinct().count() != manifest["book_count"]:
            raise ValueError("Invalid book cardinality")
        if docs.count() != manifest["book_count"] or docs.select("text_file").distinct().count() != manifest["book_count"]:
            raise ValueError("Invalid document cardinality")

        # Reúne metadados, textos e hashes; interrompe o fluxo se houver dados obrigatórios ausentes.
        combined = books.join(docs, "text_file", "left").join(expected_hash, "text_file", "left")
        invalid = combined.filter("book_id IS NULL OR title IS NULL OR trim(title) = '' OR author IS NULL OR text IS NULL OR content_sha256 IS NULL")
        if invalid.limit(1).count():
            raise ValueError("Source validation failure: load blocked")

        # Valida novamente os textos após a leitura pelo Spark.
        if combined.filter(F.sha2("text", 256) != F.col("content_sha256")).limit(1).count():
            raise ValueError("Document checksum mismatch: load blocked")

        # Extrai o corpo delimitado no texto e bloqueia conteúdo vazio ou sem os marcadores esperados.
        body = F.regexp_extract(F.col("text"), BODY_PATTERN, 1)
        prepared = combined.withColumn("body", body)
        if prepared.filter(F.length(F.trim("body")) == 0).limit(1).count():
            raise ValueError("START/END markers missing or empty: load blocked")

        # Normaliza e identifica tokens para calcular as métricas de cada livro.
        prepared = prepared.withColumn("tokens", F.regexp_extract_all(F.lower("body"), F.lit(TOKEN_PATTERN), F.lit(0)))
        result = prepared.select(
            "book_id", "title", "author", "language", "text_source", "content_sha256",
            F.length("body").alias("body_char_count"), F.size("tokens").alias("word_count"),
            F.expr("size(filter(tokens, x -> x = 'alice'))").alias("alice_mentions"),
            F.expr("size(filter(tokens, x -> x = 'monster'))").alias("monster_mentions"),
            F.lit(manifest["batch_id"]).alias("source_batch_id")).cache()

        # Materializa e valida o resultado antes de gravar qualquer dado na tabela de destino.
        if result.count() != manifest["book_count"] or result.filter("word_count <= 0").limit(1).count():
            raise ValueError("Feature validation failed: load blocked")
        result.show(truncate=False)

        # Cria o namespace se necessário e substitui a tabela Iceberg pelo resultado validado.
        spark.sql("CREATE NAMESPACE IF NOT EXISTS lake.etl")
        (result.writeTo(settings()["table"]).using("iceberg")
         .tableProperty("format-version", "2").tableProperty("write.format.default", "parquet").createOrReplace())
        print(json.dumps({"status": "loaded", "rows": manifest["book_count"], "batch_id": manifest["batch_id"]}))
    finally:
        # Libera o cache e encerra a sessão mesmo se alguma validação ou gravação falhar.
        if result is not None:
            result.unpersist()
        spark.stop()


if __name__ == "__main__":
    # Executa o pipeline quando o arquivo é chamado diretamente.
    main()
