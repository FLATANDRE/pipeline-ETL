-- Resultado analítico: apenas dados preparados.
SELECT book_id, title, author, word_count, alice_mentions, monster_mentions
FROM lake.etl.book_features ORDER BY book_id;

-- Rastreabilidade até a extração.
SELECT book_id, content_sha256, source_batch_id
FROM lake.etl.book_features ORDER BY book_id;

-- Snapshots: reexecutar pode criar um novo snapshot, mas não duplicar as linhas atuais.
SELECT committed_at, snapshot_id, operation
FROM lake.etl."book_features$snapshots" ORDER BY committed_at DESC;

-- Arquivos da tabela atual: Parquet no SILO.
SELECT file_path, record_count
FROM lake.etl."book_features$files";
