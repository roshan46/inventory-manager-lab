"""Deploy by SSM; probe from the instance because ingress is learner-only."""
import json
import os
import shlex
import time
import boto3


def commands(outputs, release):
    quote = shlex.quote
    region = os.environ["AWS_REGION"]
    registry = release["image"].split("/")[0]
    env = {"AWS_REGION": region, "DB_HOST": outputs["db_host"], "DB_SECRET_ARN": outputs["db_secret_arn"], "APP_VERSION": release["sha"]}
    # No secret values enter command payloads or command output.
    lines = ["#!/bin/bash", "set -euo pipefail", "cloud-init status --wait", "test -f /opt/inventory/host-ready",
             "exec 9>/opt/inventory/deploy.lock", "flock -w 60 9", "umask 077",
             f"aws ecr get-login-password --region {quote(region)} | docker login --username AWS --password-stdin {quote(registry)}",
             f"docker pull {quote(release['image'])}",
             "printf '%s\\n' " + " ".join(quote(k + "=" + v) for k, v in env.items()) + " > /opt/inventory/runtime.env",
             "printf 'APP_SECRET=%s\\n' \"$(cat /opt/inventory/app-secret)\" >> /opt/inventory/runtime.env",
             f"docker run --rm --env-file /opt/inventory/runtime.env {quote(release['image'])} flask --app app init-db",
             "docker rm -f inventory-app 2>/dev/null || true",
             "docker run -d --name inventory-app --restart unless-stopped --env-file /opt/inventory/runtime.env "
             "--cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m "
             f"-p 8000:8000 --log-driver awslogs --log-opt awslogs-region={quote(region)} "
             f"--log-opt awslogs-group={quote(outputs['log_group'])} --log-opt awslogs-stream=app-{quote(release['sha'])} {quote(release['image'])}",
             "ready=0; for n in $(seq 1 60); do if curl -fsS http://localhost:8000/health/ready; then ready=1; break; fi; sleep 3; done",
             "test \"$ready\" = 1",
             "curl -fsS http://localhost:8000/version > /opt/inventory/version.json",
             "python3 -c " + quote("import json; assert json.load(open('/opt/inventory/version.json'))['version'] == " + repr(release["sha"])),
             "docker logout " + quote(registry)]
    return "\n".join(lines)


def deploy(outputs, release):
    ssm = boto3.client("ssm")
    instance = outputs["instance_id"]
    for _ in range(60):
        info = ssm.describe_instance_information(Filters=[{"Key": "InstanceIds", "Values": [instance]}])["InstanceInformationList"]
        if info and info[0]["PingStatus"] == "Online":
            break
        time.sleep(10)
    else:
        raise RuntimeError("Instance did not become SSM Online within 10 minutes")
    command_id = ssm.send_command(InstanceIds=[instance], DocumentName="AWS-RunShellScript",
        Parameters={"commands": ["bash -se <<'INVENTORY_DEPLOY'\n" + commands(outputs, release) + "\nINVENTORY_DEPLOY"], "executionTimeout": ["900"]}, TimeoutSeconds=120)["Command"]["CommandId"]
    for _ in range(100):
        try:
            invocation = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance)
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(10)
            continue
        if invocation["Status"] == "Success":
            print("Container ready; release verified:", release["sha"])
            return
        if invocation["Status"] in {"Failed", "Cancelled", "TimedOut", "Cancelling"}:
            raise RuntimeError(f"SSM deployment {command_id} {invocation['Status']}. Inspect SSM output and CloudWatch logs; use manual rollback if needed.")
        time.sleep(10)
    raise RuntimeError("Deployment polling timed out; inspect SSM before retrying")
