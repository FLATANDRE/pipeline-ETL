import os
import requests


def query(sql):
    base = os.environ.get("TRINO_URI", "http://trino:8080")
    headers = {"X-Trino-User": "etl-demo", "X-Trino-Source": "etl-lab"}
    r = requests.post(base + "/v1/statement", data=sql.encode("utf-8"), headers=headers, timeout=30)
    r.raise_for_status()
    rows, columns = [], []
    while True:
        payload = r.json()
        if "error" in payload:
            raise RuntimeError(str(payload["error"]))
        if "columns" in payload:
            columns = [c["name"] for c in payload["columns"]]
        rows.extend(payload.get("data", []))
        if not payload.get("nextUri"):
            return [dict(zip(columns, row)) for row in rows]
        r = requests.get(payload["nextUri"], headers=headers, timeout=60)
        r.raise_for_status()
