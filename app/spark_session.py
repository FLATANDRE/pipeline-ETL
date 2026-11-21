from pathlib import Path
from app.settings import settings


def spark_session():
    from pyspark.sql import SparkSession
    c = settings()
    jars = sorted(str(p) for p in Path("/opt/iceberg-jars").glob("*.jar"))
    if len(jars) != 2:
        raise RuntimeError("Expected the Iceberg Spark runtime and AWS bundle JARs")
    props = {
        "spark.jars": ",".join(jars),
        "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        "spark.sql.catalog.lake": "org.apache.iceberg.spark.SparkCatalog",
        "spark.sql.catalog.lake.type": "rest",
        "spark.sql.catalog.lake.uri": c["polaris"] + "/api/catalog",
        "spark.sql.catalog.lake.warehouse": c["catalog"],
        "spark.sql.catalog.lake.credential": c["client_id"] + ":" + c["client_secret"],
        "spark.sql.catalog.lake.oauth2-server-uri": c["polaris"] + "/api/catalog/v1/oauth/tokens",
        "spark.sql.catalog.lake.scope": "PRINCIPAL_ROLE:ALL",
        "spark.sql.catalog.lake.header.Polaris-Realm": c["realm"],
        "spark.sql.catalog.lake.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
        "spark.sql.catalog.lake.s3.endpoint": c["endpoint"],
        "spark.sql.catalog.lake.s3.path-style-access": "true",
        "spark.sql.catalog.lake.s3.access-key-id": c["access_key"],
        "spark.sql.catalog.lake.s3.secret-access-key": c["secret_key"],
        "spark.sql.catalog.lake.client.region": c["region"],
        "spark.sql.session.timeZone": "UTC",
        "spark.sql.shuffle.partitions": "2",
        "spark.ui.enabled": "false",
        "spark.driver.memory": "1g",
        "spark.driver.host": "127.0.0.1",
        "spark.driver.bindAddress": "127.0.0.1",
    }
    b = SparkSession.builder.master("local[2]").appName("etl-books-no-broker")
    for key, value in props.items():
        b = b.config(key, value)
    return b.getOrCreate()
