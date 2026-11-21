import os


def env(name, default):
    return os.environ.get(name, default)


def settings():
    return {
        "endpoint": env("S3_ENDPOINT", "http://silo:9000"),
        "access_key": env("S3_ACCESS_KEY", "labadmin"),
        "secret_key": env("S3_SECRET_KEY", "local-only-change-me-2026"),
        "region": env("AWS_REGION", "us-east-1"),
        "polaris": env("POLARIS_URI", "http://polaris:8181"),
        "client_id": env("POLARIS_CLIENT_ID", "lab-admin"),
        "client_secret": env("POLARIS_CLIENT_SECRET", "local-polaris-secret"),
        "realm": env("POLARIS_REALM", "POLARIS"),
        "catalog": "lakehouse", "bucket": "warehouse", "table": "lake.etl.book_features",
    }
