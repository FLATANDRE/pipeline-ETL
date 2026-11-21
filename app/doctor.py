import json
import requests
import boto3
from botocore.client import Config
from app.bootstrap import wait
from app.settings import settings
from app.trino_client import query


def main():
    c = settings()
    client = boto3.client("s3", endpoint_url=c["endpoint"], aws_access_key_id=c["access_key"],
        aws_secret_access_key=c["secret_key"], region_name=c["region"],
        config=Config(s3={"addressing_style": "path"}))
    wait(lambda: client.head_bucket(Bucket=c["bucket"]), "SILO bucket")
    def health():
        r = requests.get("http://polaris:8182/q/health/ready", timeout=10)
        r.raise_for_status()
        return r.json()
    wait(health, "Polaris")
    catalogs = wait(lambda: query("SHOW CATALOGS"), "Trino")
    if {"Catalog": "lake"} not in catalogs:
        raise RuntimeError("Trino did not load the lake catalog")
    wait(lambda: query("SHOW SCHEMAS FROM lake"), "Trino/Polaris catalog connection")
    print(json.dumps({"status": "PASS", "checks": ["SILO bucket", "Polaris health", "Trino catalog/Polaris"]}))


if __name__ == "__main__":
    main()
