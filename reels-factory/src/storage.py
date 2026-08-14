"""Upload su Cloudflare R2 (S3-compatibile). Instagram richiede che il video
sia raggiungibile da un URL pubblico durante la pubblicazione."""

import os
from pathlib import Path

import boto3
from botocore.config import Config


def _client():
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_clip(local_path: Path, key: str) -> str:
    """Carica il file e ritorna l'URL con cui Instagram potrà scaricarlo.

    Se R2_PUBLIC_BASE_URL è impostato (bucket con dominio pubblico / r2.dev),
    usa quello. Altrimenti genera un URL firmato valido 48 ore.
    """
    bucket = os.environ["R2_BUCKET"]
    client = _client()
    client.upload_file(
        str(local_path), bucket, key,
        ExtraArgs={"ContentType": "video/mp4"},
    )

    public_base = os.environ.get("R2_PUBLIC_BASE_URL", "").rstrip("/")
    if public_base:
        return f"{public_base}/{key}"
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=48 * 3600,
    )


def refresh_url(key: str) -> str:
    """URL fresco per una clip già caricata (usato al momento della pubblicazione,
    perché un URL firmato generato giorni prima potrebbe essere scaduto)."""
    public_base = os.environ.get("R2_PUBLIC_BASE_URL", "").rstrip("/")
    if public_base:
        return f"{public_base}/{key}"
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": os.environ["R2_BUCKET"], "Key": key},
        ExpiresIn=48 * 3600,
    )
