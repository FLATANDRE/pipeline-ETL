# Proveniência dos dados

As fontes completas estão incluídas; não é preciso acessar APIs durante a demonstração.

- `source/books.csv`: seleção de metadados bibliográficos dos livros 11 e 84 do Project Gutenberg. CSV criado para relacionar os documentos, não uma base de vendas simulada.
- `source/texts/pg11.txt`: Alice's Adventures in Wonderland, Lewis Carroll. https://www.gutenberg.org/ebooks/11
- `source/texts/pg84.txt`: Frankenstein; or, The Modern Prometheus, Mary Wollstonecraft Shelley. https://www.gutenberg.org/ebooks/84
- Downloads: https://www.gutenberg.org/ebooks/11.txt.utf-8 e https://www.gutenberg.org/ebooks/84.txt.utf-8 ; obtidos em 2026-11-07.
- `source/SHA256SUMS.json`: hashes SHA-256 dos bytes distribuídos.
- `expected/features.json`: resultados calculados pela regra explícita em `app/rules.py`, utilizados na validação.

São textos reais; não há dados pessoais ou métricas sintéticas de clientes. Os documentos preservam seus avisos e a licença Project Gutenberg. Segundo o acervo, estas obras são de domínio público nos EUA; verifique legislação local e os termos de redistribuição. A licença MIT do código não substitui os avisos dos documentos ou licenças das dependências.

## Regra textual

Extrair o conteúdo entre os marcadores START e END; aplicar minúsculas; contar tokens `[a-z]+`. A contagem inclui títulos, sumários e notas que estiverem dentro desses limites. `alice_mentions` e `monster_mentions` contam tokens exatos.

Preservar os bytes originais e decodificar UTF-8 sem normalizar CRLF. `body_char_count` muda se normalizar fins de linha. As contagens pertencem à edição e à regra distribuídas, não são valores universais das obras. Extração lexical NÃO é análise semântica ou modelo de IA.

O CSV é estruturado. O conteúdo literário TXT é não estruturado. O processamento produz features estruturadas a partir desse texto.
