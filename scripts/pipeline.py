"""Trusted-main release pipeline. Saved plans are private and never silently regenerated."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import boto3

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".plan"


def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=capture).stdout


def tf(*args, capture=False):
    return run("terraform", "-chdir=infra/dev", *args, capture=capture)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identifier(value, kind="sha"):
    pattern = r"[0-9a-f]{40}" if kind == "sha" else r"[0-9]+"
    if not re.fullmatch(pattern, value):
        raise ValueError(f"Invalid {kind}")
    return value


def require_environment():
    for key in ("AWS_REGION", "STATE_BUCKET", "ARTIFACT_BUCKET", "ECR_REPOSITORY", "GITHUB_SHA", "GITHUB_REPOSITORY", "GH_TOKEN", "LEARNER_CIDR", "AMI_ID"):
        if not os.environ.get(key):
            raise ValueError(f"Missing {key}")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("Only main can deploy")
    identifier(os.environ["GITHUB_SHA"])
    WORK.mkdir(exist_ok=True)


def api(path):
    request = urllib.request.Request("https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"] + path,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def current_main():
    if api("/git/ref/heads/main")["object"]["sha"] != os.environ["GITHUB_SHA"]:
        raise ValueError("Main changed; start a fresh workflow")


def verify_run(run_id, path, sha, event):
    data = api("/actions/runs/" + identifier(str(run_id), "run ID"))
    if (data["conclusion"] != "success" or data["head_branch"] != "main" or
        data["head_sha"] != sha or data["path"] != path or data["event"] != event):
        raise ValueError("Workflow run identity or status mismatch")


def get_json(key):
    return json.loads(boto3.client("s3").get_object(Bucket=os.environ["ARTIFACT_BUCKET"], Key=key)["Body"].read())


def put_json(key, data):
    boto3.client("s3").put_object(Bucket=os.environ["ARTIFACT_BUCKET"], Key=key,
        Body=json.dumps(data).encode(), ContentType="application/json", IfNoneMatch="*")


def target():
    return {key: os.environ[key] for key in ("AWS_REGION", "STATE_BUCKET", "ARTIFACT_BUCKET", "ECR_REPOSITORY", "LEARNER_CIDR", "AMI_ID")}


def initialize():
    tf("init", "-input=false", "-lockfile=readonly", "-backend-config=bucket=" + os.environ["STATE_BUCKET"],
       "-backend-config=key=dev/inventory-manager/terraform.tfstate", "-backend-config=region=" + os.environ["AWS_REGION"],
       "-backend-config=encrypt=true", "-backend-config=use_lockfile=true")
    if tf("workspace", "show", capture=True).strip() != "default":
        raise ValueError("Only the default workspace is supported for dev")


def validate_release(release, sha, repository, ecr):
    identifier(sha)
    if release["sha"] != sha or release["repository"] != repository:
        raise ValueError("Release commit/repository mismatch")
    if not re.fullmatch(re.escape(ecr) + r"@sha256:[0-9a-f]{64}", release["image"]):
        raise ValueError("Release must reference an immutable digest in the configured ECR repository")


def release_for(sha):
    release = get_json("releases/" + identifier(sha) + ".json")
    validate_release(release, sha, os.environ["GITHUB_REPOSITORY"], os.environ["ECR_REPOSITORY"])
    verify_run(release["run_id"], ".github/workflows/build.yml", sha, "push")
    return release


def record_release():
    # Called only after the tested image was successfully pushed. The consuming
    # plan additionally verifies that this entire build workflow succeeded.
    sha = identifier(os.environ["GITHUB_SHA"])
    image = os.environ["ECR_REPOSITORY"] + "@" + os.environ["IMAGE_DIGEST"]
    release = {"sha": sha, "image": image, "repository": os.environ["GITHUB_REPOSITORY"], "run_id": os.environ["GITHUB_RUN_ID"]}
    validate_release(release, sha, release["repository"], os.environ["ECR_REPOSITORY"])
    put_json("releases/" + sha + ".json", release)


def make_plan(operation, sha=None):
    require_environment()
    current_main()
    if operation not in {"deploy", "destroy"}:
        raise ValueError("Invalid operation")
    release = release_for(sha) if operation == "deploy" else None
    initialize()
    inputs = WORK / "inputs.tfvars.json"
    inputs.write_text(json.dumps({"aws_region": os.environ["AWS_REGION"], "learner_cidr": os.environ["LEARNER_CIDR"], "ami_id": os.environ["AMI_ID"]}))
    plan = WORK / "deployment.tfplan"
    args = ["plan", "-input=false", "-lock-timeout=60s", "-var-file=" + str(inputs), "-out=" + str(plan)]
    if operation == "destroy":
        args.append("-destroy")
    tf(*args)
    version = json.loads(run("terraform", "version", "-json", capture=True))["terraform_version"]
    manifest = {"sha": os.environ["GITHUB_SHA"], "repository": os.environ["GITHUB_REPOSITORY"], "target": target(),
                "operation": operation, "release": release, "terraform_version": version,
                "created_at": datetime.now(timezone.utc).isoformat(), "checksum": sha256(plan)}
    prefix = "plans/" + identifier(os.environ["GITHUB_RUN_ID"], "run ID")
    boto3.client("s3").put_object(Bucket=os.environ["ARTIFACT_BUCKET"], Key=prefix + "/plan", Body=plan.read_bytes(), IfNoneMatch="*")
    put_json(prefix + "/manifest.json", manifest)
    with open(os.environ.get("GITHUB_STEP_SUMMARY", WORK / "summary.txt"), "a") as summary:
        summary.write(f"\nPlan ID: {os.environ['GITHUB_RUN_ID']}\nOperation: {operation}\nInfrastructure commit: {manifest['sha']}\nRelease: {release}\nReview the plan log before dispatching apply. Expires in 24 hours.\n")


def validate_manifest(manifest, sha, repository, operation, expected_target, now=None):
    if manifest["sha"] != sha or manifest["repository"] != repository:
        raise ValueError("Plan commit/repository mismatch")
    if manifest["operation"] != operation or manifest["target"] != expected_target:
        raise ValueError("Operation or deployment target mismatch")
    age = (now or datetime.now(timezone.utc)) - datetime.fromisoformat(manifest["created_at"])
    if age < timedelta(0) or age > timedelta(hours=24):
        raise ValueError("Plan expired; create and review a new plan")


def apply_plan(run_id, operation):
    require_environment()
    current_main()
    verify_run(run_id, ".github/workflows/plan.yml", os.environ["GITHUB_SHA"], "workflow_dispatch")
    prefix = "plans/" + identifier(run_id, "run ID")
    manifest = get_json(prefix + "/manifest.json")
    validate_manifest(manifest, os.environ["GITHUB_SHA"], os.environ["GITHUB_REPOSITORY"], operation, target())
    if operation == "deploy":
        release = release_for(manifest["release"]["sha"])
        if release != manifest["release"]:
            raise ValueError("Release changed since planning")
    plan = WORK / "deployment.tfplan"
    boto3.client("s3").download_file(os.environ["ARTIFACT_BUCKET"], prefix + "/plan", str(plan))
    if sha256(plan) != manifest["checksum"]:
        raise ValueError("Plan checksum mismatch")
    initialize()
    if json.loads(run("terraform", "version", "-json", capture=True))["terraform_version"] != manifest["terraform_version"]:
        raise ValueError("Terraform version mismatch")
    current_main()
    tf("apply", "-input=false", "-lock-timeout=60s", str(plan))
    if operation == "deploy":
        deploy_release(release)
    elif tf("state", "list", capture=True).strip():
        raise ValueError("Resources remain in state; inspect teardown")


def deploy_release(release):
    from deploy_ec2 import deploy
    outputs = {k: v["value"] for k, v in json.loads(tf("output", "-json", capture=True)).items()}
    deploy(outputs, release)
    # Each deployment has its own immutable success marker.
    put_json("successful/" + os.environ["GITHUB_RUN_ID"] + ".json", {"release": release, "repository": os.environ["GITHUB_REPOSITORY"]})


def rollback(run_id):
    require_environment()
    current_main()
    marker = get_json("successful/" + identifier(run_id, "run ID") + ".json")
    release = release_for(marker["release"]["sha"])
    if marker["repository"] != os.environ["GITHUB_REPOSITORY"] or marker["release"] != release:
        raise ValueError("Previous successful release mismatch")
    initialize()
    deploy_release(release)


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "release":
        record_release()
    elif command == "plan":
        make_plan(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif command == "apply":
        apply_plan(sys.argv[2], sys.argv[3])
    elif command == "rollback":
        rollback(sys.argv[2])
    else:
        raise ValueError("Unknown command")
