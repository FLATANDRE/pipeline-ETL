import json
import time
from pathlib import Path
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import requests
from app.settings import settings


def wait(fn, label, attempts=90):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {label}: {last}")


def trino_properties(c):
    return "\n".join([
        "connector.name=iceberg", "iceberg.catalog.type=rest",
        "iceberg.rest-catalog.uri=" + c["polaris"] + "/api/catalog",
        "iceberg.rest-catalog.warehouse=" + c["catalog"],
        "iceberg.rest-catalog.security=OAUTH2",
        "iceberg.rest-catalog.oauth2.credential=" + c["client_id"] + ":" + c["client_secret"],
        "iceberg.rest-catalog.oauth2.server-uri=" + c["polaris"] + "/api/catalog/v1/oauth/tokens",
        "iceberg.rest-catalog.oauth2.scope=PRINCIPAL_ROLE:ALL",
        "iceberg.rest-catalog.http-headers=Polaris-Realm: " + c["realm"],
        "iceberg.rest-catalog.vended-credentials-enabled=false",
        "fs.s3.enabled=true", "s3.endpoint=" + c["endpoint"],
        "s3.path-style-access=true", "s3.aws-access-key=" + c["access_key"],
        "s3.aws-secret-key=" + c["secret_key"], "s3.region=" + c["region"], "",
    ])


def main():
    c = settings()
    s3 = boto3.client("s3", endpoint_url=c["endpoint"], aws_access_key_id=c["access_key"],
                      aws_secret_access_key=c["secret_key"], region_name=c["region"],
                      config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
    wait(s3.list_buckets, "SILO")
    try:
        s3.head_bucket(Bucket=c["bucket"])
    except ClientError as exc:
        if str(exc.response["Error"]["Code"]) not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        s3.create_bucket(Bucket=c["bucket"])
    def authenticate():
        r = requests.post(c["polaris"] + "/api/catalog/v1/oauth/tokens",
            headers={"Polaris-Realm": c["realm"]},
            data={"grant_type": "client_credentials", "client_id": c["client_id"],
                  "client_secret": c["client_secret"], "scope": "PRINCIPAL_ROLE:ALL"}, timeout=15)
        r.raise_for_status()
        return r.json()["access_token"]
    token = wait(authenticate, "Polaris OAuth")
    headers = {"Authorization": "Bearer " + token, "Polaris-Realm": c["realm"]}
    base = c["polaris"] + "/api/management/v1"
    def call(method, path, body=None, allow_exists=False):
        r = requests.request(method, base + path, headers=headers, json=body, timeout=30)
        if allow_exists and r.status_code == 409:
            return r
        if not r.ok:
            raise RuntimeError(f"Polaris {method} {path}: {r.status_code} {r.text}")
        return r
    catalog = {"name": c["catalog"], "type": "INTERNAL",
        "properties": {"default-base-location": "s3://warehouse/iceberg"},
        "storageConfigInfo": {"storageType": "S3", "allowedLocations": ["s3://warehouse/"],
            "endpoint": c["endpoint"], "endpointInternal": c["endpoint"],
            "region": c["region"], "pathStyleAccess": True, "stsUnavailable": True}}
    created = call("POST", "/catalogs", {"catalog": catalog}, allow_exists=True)
    if created.status_code == 409:
        current = call("GET", "/catalogs/" + c["catalog"]).json()
        if current["properties"].get("default-base-location") != catalog["properties"]["default-base-location"]:
            raise RuntimeError("Existing catalog location differs; do not silently reuse it")
        if current["storageConfigInfo"].get("endpoint") != c["endpoint"]:
            raise RuntimeError("Existing catalog endpoint differs")
    roles = "/catalogs/" + c["catalog"] + "/catalog-roles"
    call("POST", roles, {"catalogRole": {"name": "lab_writer"}}, allow_exists=True)
    grant = {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}
    grants = call("GET", roles + "/lab_writer/grants").json()["grants"]
    if grant not in grants:
        call("PUT", roles + "/lab_writer/grants", {"grant": grant})
    principal_roles_path = "/principal-roles/service_admin/catalog-roles/" + c["catalog"]
    principal_roles = call("GET", principal_roles_path).json()["roles"]
    if not any(role.get("name") == "lab_writer" for role in principal_roles):
        call("PUT", principal_roles_path, {"catalogRole": {"name": "lab_writer"}})
    path = Path("/opt/airflow/generated/lake.properties")
    path.write_text(trino_properties(c))
    path.chmod(0o644)
    print(json.dumps({"status": "ready", "catalog": c["catalog"], "bucket": c["bucket"]}))


if __name__ == "__main__":
    main()
