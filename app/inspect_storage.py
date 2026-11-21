import json
import boto3
from botocore.client import Config
from app.settings import settings


def main():
    c = settings()
    client = boto3.client("s3", endpoint_url=c["endpoint"], aws_access_key_id=c["access_key"],
        aws_secret_access_key=c["secret_key"], region_name=c["region"],
        config=Config(s3={"addressing_style": "path"}))
    count = 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=c["bucket"]):
        for obj in page.get("Contents", []):
            print(json.dumps({"key": obj["Key"], "bytes": obj["Size"]}))
            count += 1
    print(json.dumps({"objects": count}))


if __name__ == "__main__":
    main()
