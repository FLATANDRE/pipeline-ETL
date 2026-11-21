import pytest
from app.trino_client import query


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_trino_pagination(monkeypatch):
    monkeypatch.setattr("app.trino_client.requests.post", lambda *a, **k: Response({"nextUri": "http://trino/next"}))
    monkeypatch.setattr("app.trino_client.requests.get", lambda *a, **k: Response({"columns": [{"name": "n"}], "data": [[2]]}))
    assert query("select 2") == [{"n": 2}]


def test_trino_error(monkeypatch):
    monkeypatch.setattr("app.trino_client.requests.post", lambda *a, **k: Response({"error": {"message": "bad SQL"}}))
    with pytest.raises(RuntimeError, match="bad SQL"):
        query("bad")


def test_trino_empty_success(monkeypatch):
    monkeypatch.setattr("app.trino_client.requests.post", lambda *a, **k: Response({}))
    assert query("DDL") == []
