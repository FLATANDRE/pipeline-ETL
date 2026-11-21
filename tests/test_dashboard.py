import pytest

st = pytest.importorskip("streamlit")
pytest.importorskip("pandas")
from streamlit.testing.v1 import AppTest

from app import trino_client


@pytest.fixture(autouse=True)
def clear_dashboard_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


@pytest.fixture
def books():
    return [
        {
            "book_id": book_id,
            "title": title,
            "author": author,
            "language": language,
            "text_source": "source",
            "content_sha256": "hash",
            "body_char_count": 100,
            "word_count": count,
            "alice_mentions": alice,
            "monster_mentions": monster,
            "source_batch_id": "batch",
        }
        for book_id, title, author, language, count, alice, monster in [
            (11, "Alice", "Carroll", "en", 27427, 399, 0),
            (84, "Frankenstein", "Shelley", "en", 75328, 0, 31),
        ]
    ]


def test_dashboard_displays_and_filters_trino_data(monkeypatch, books):
    queries = []
    monkeypatch.setattr(trino_client, "query", lambda sql: queries.append(sql) or books)
    app = AppTest.from_file("dashboard/dashboard.py").run()

    assert not app.exception
    assert "lake.etl.book_features" in queries[0]
    assert [metric.value for metric in app.metric] == ["2", "102,755", "399", "31"]

    app.multiselect[0].select("Carroll").run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["1", "27,427", "399", "0"]
    assert len(queries) == 1
    app.button[0].click().run()
    assert len(queries) == 2


def test_dashboard_explains_empty_table(monkeypatch):
    monkeypatch.setattr(trino_client, "query", lambda sql: [])
    app = AppTest.from_file("dashboard/dashboard.py").run()
    assert not app.exception
    assert "não contém livros" in app.info[0].value


def test_dashboard_reports_trino_error(monkeypatch):
    def fail(sql):
        raise RuntimeError("table not found")

    monkeypatch.setattr(trino_client, "query", fail)
    app = AppTest.from_file("dashboard/dashboard.py").run()
    assert not app.exception
    assert "table not found" in app.error[0].value
