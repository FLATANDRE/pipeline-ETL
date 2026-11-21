import pandas as pd
import requests
import streamlit as st

from app.trino_client import query


SQL = """
SELECT book_id, title, author, language, text_source, content_sha256,
       body_char_count, word_count, alice_mentions, monster_mentions, source_batch_id
FROM lake.etl.book_features
ORDER BY book_id
"""

st.set_page_config(page_title="Biblioteca | Book features", page_icon="📚", layout="wide")


@st.cache_data(ttl=60, show_spinner="Consultando o Trino...")
def load_books():
    return query(SQL)


st.title("📚 Biblioteca em números")
st.caption("Dados da tabela Iceberg lake.etl.book_features, consultados pelo Trino.")

if st.sidebar.button("Atualizar dados"):
    load_books.clear()

try:
    rows = load_books()
except (requests.RequestException, RuntimeError) as exc:
    st.error(f"Não foi possível consultar a tabela no Trino: {exc}")
    st.info("Verifique se o Trino está disponível e se o pipeline ETL já foi executado.")
    st.stop()

if not rows:
    st.info("A tabela não contém livros. Execute o pipeline ETL e atualize o dashboard.")
    st.stop()

books = pd.DataFrame(rows)
st.sidebar.header("Filtros")
authors = sorted(books["author"].dropna().unique())
languages = sorted(books["language"].dropna().unique())
selected_authors = st.sidebar.multiselect("Autores", authors)
selected_languages = st.sidebar.multiselect("Idiomas", languages)

filtered = books
if selected_authors:
    filtered = filtered[filtered["author"].isin(selected_authors)]
if selected_languages:
    filtered = filtered[filtered["language"].isin(selected_languages)]

if filtered.empty:
    st.warning("Nenhum livro corresponde aos filtros selecionados.")
    st.stop()

metrics = st.columns(4)
metrics[0].metric("Livros", f"{len(filtered):,}")
metrics[1].metric("Tokens", f"{filtered['word_count'].sum():,}")
metrics[2].metric("Menções a alice", f"{filtered['alice_mentions'].sum():,}")
metrics[3].metric("Menções a monster", f"{filtered['monster_mentions'].sum():,}")

chart_data = filtered.copy()
chart_data["livro"] = chart_data["title"] + " (ID " + chart_data["book_id"].astype(str) + ")"
chart_data = chart_data.set_index("livro")

left, right = st.columns(2)
with left:
    st.subheader("Tokens por livro")
    st.bar_chart(chart_data["word_count"], horizontal=True)
with right:
    st.subheader("Menções por livro")
    st.bar_chart(chart_data[["alice_mentions", "monster_mentions"]], horizontal=True)

st.subheader("Dados dos livros")
st.dataframe(
    filtered.rename(columns={
        "book_id": "ID",
        "title": "Título",
        "author": "Autor",
        "language": "Idioma",
        "body_char_count": "Caracteres",
        "word_count": "Tokens",
        "alice_mentions": "alice",
        "monster_mentions": "monster",
        "text_source": "Fonte",
        "content_sha256": "SHA-256",
        "source_batch_id": "Lote",
    }),
    hide_index=True,
    width="stretch",
)
st.caption(
    "Tokens seguem a regra [a-z]+ em minúsculas; as menções contam tokens exatos. "
    "O cache expira após 60 segundos; uma interação ou o botão lateral consulta os dados novamente."
)
