"""Real Docker lifecycle check in an isolated inventory-ci Compose project."""
import http.cookiejar
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from check_http_connections import check as check_idle_connections


def compose(*args, capture=False):
    return subprocess.run(["docker", "compose", "-p", "inventory-ci", *args], check=True, text=True, capture_output=capture).stdout


def ready(expected=200):
    for _ in range(90):
        try:
            with urllib.request.urlopen("http://localhost:8001/health/ready", timeout=5) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            status = 0
        if status == expected:
            return
        time.sleep(2)
    raise AssertionError(f"Readiness did not become {expected}")


def main():
    compose("up", "--build", "-d", "--wait", "--wait-timeout", "180")
    ready()
    check_idle_connections()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    html = opener.open("http://localhost:8001/").read().decode()
    token = re.search(r'name="csrf" value="([^"]+)"', html)[1]
    code = "SMOKE-" + str(time.time_ns())
    response = opener.open("http://localhost:8001/products", data=urllib.parse.urlencode({"csrf": token, "code": code, "name": "Persistent widget"}).encode())
    assert code in response.read().decode()
    uid = compose("exec", "-T", "app", "id", "-u", capture=True).strip()
    assert uid == "10001", uid
    compose("up", "-d", "--force-recreate", "app")
    ready()
    assert code in opener.open("http://localhost:8001/").read().decode()
    compose("stop", "db")
    ready(503)
    assert urllib.request.urlopen("http://localhost:8001/health/live").status == 200
    compose("start", "db")
    ready()
    print("Compose creation, non-root runtime, persistence, database failure and recovery passed.")


if __name__ == "__main__":
    main()
