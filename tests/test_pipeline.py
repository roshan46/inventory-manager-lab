from datetime import datetime, timezone, timedelta
import pytest
from pipeline import validate_release, validate_manifest, identifier
from deploy_ec2 import commands

SHA = "a" * 40
ECR = "123456789012.dkr.ecr.us-east-2.amazonaws.com/inventory-manager"


def test_release():
    release = {"sha": SHA, "repository": "owner/repo", "image": ECR + "@sha256:" + "b" * 64}
    validate_release(release, SHA, "owner/repo", ECR)
    for field, value in [("sha", "c" * 40), ("repository", "evil/repo"), ("image", ECR + ":latest"), ("image", "evil@sha256:" + "b" * 64)]:
        with pytest.raises(ValueError):
            validate_release(release | {field: value}, SHA, "owner/repo", ECR)


def test_reviewed_plan():
    now = datetime.now(timezone.utc)
    manifest = {"sha": SHA, "repository": "owner/repo", "operation": "deploy", "target": {"bucket": "a"}, "created_at": now.isoformat()}
    validate_manifest(manifest, SHA, "owner/repo", "deploy", {"bucket": "a"}, now)
    for changed in [{"sha": "b" * 40}, {"repository": "other/repo"}, {"operation": "destroy"}, {"target": {"bucket": "other"}}, {"created_at": (now-timedelta(hours=25)).isoformat()}, {"created_at": (now+timedelta(hours=1)).isoformat()}]:
        with pytest.raises(ValueError):
            validate_manifest(manifest | changed, SHA, "owner/repo", "deploy", {"bucket": "a"}, now)


def test_shell_payload(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    payload = commands({"db_host": "host", "db_secret_arn": "arn:secret", "log_group": "/logs"}, {"sha": SHA, "image": ECR + "@sha256:" + "b" * 64})
    assert "--read-only" in payload and "flock" in payload
    assert "get-secret-value" not in payload
    assert "health/ready" in payload and "/version" in payload
    assert payload.index("init-db") < payload.index("docker rm -f")


@pytest.mark.parametrize("value", ["../plans", "123;echo hi", "latest", ""])
def test_invalid_ids(value):
    with pytest.raises(ValueError):
        identifier(value, "run ID")


@pytest.mark.parametrize("failure", ["checksum", "stale-state", "release-changed"])
def test_apply_refuses_unreviewed_or_stale_changes(monkeypatch, tmp_path, failure):
    import hashlib
    import json
    import subprocess
    import pipeline
    monkeypatch.setattr(pipeline, "WORK", tmp_path)
    for key, value in {"GITHUB_SHA": SHA, "GITHUB_REPOSITORY": "owner/repo", "ARTIFACT_BUCKET": "private"}.items():
        monkeypatch.setenv(key, value)
    release = {"sha": SHA, "repository": "owner/repo", "image": ECR + "@sha256:" + "b" * 64}
    manifest = {"sha": SHA, "repository": "owner/repo", "operation": "deploy", "target": {},
                "created_at": datetime.now(timezone.utc).isoformat(), "release": release,
                "terraform_version": "1.16.1", "checksum": hashlib.sha256(b"reviewed").hexdigest()}
    calls = []
    monkeypatch.setattr(pipeline, "require_environment", lambda: None)
    monkeypatch.setattr(pipeline, "current_main", lambda: None)
    monkeypatch.setattr(pipeline, "verify_run", lambda *args: None)
    monkeypatch.setattr(pipeline, "target", lambda: {})
    monkeypatch.setattr(pipeline, "initialize", lambda: None)
    monkeypatch.setattr(pipeline, "get_json", lambda key: manifest)
    monkeypatch.setattr(pipeline, "release_for", lambda sha: release | ({"image": "changed"} if failure == "release-changed" else {}))
    monkeypatch.setattr(pipeline, "run", lambda *args, **kwargs: json.dumps({"terraform_version": "1.16.1"}))
    monkeypatch.setattr(pipeline, "deploy_release", lambda release: calls.append("deploy"))

    class S3:
        def download_file(self, bucket, key, path):
            from pathlib import Path
            Path(path).write_bytes(b"tampered" if failure == "checksum" else b"reviewed")

    monkeypatch.setattr(pipeline.boto3, "client", lambda *args: S3())

    def terraform(*args, **kwargs):
        calls.append(args[0])
        raise subprocess.CalledProcessError(1, "terraform apply", stderr="Saved plan is stale")

    monkeypatch.setattr(pipeline, "tf", terraform)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        pipeline.apply_plan("123", "deploy")
    assert "deploy" not in calls and "plan" not in calls
    assert calls == (["apply"] if failure == "stale-state" else [])
