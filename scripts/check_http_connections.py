"""Ensure browser-style idle connections cannot occupy all HTTP workers."""
from contextlib import ExitStack
import socket
import time
import urllib.request


def check(host="127.0.0.1", port=8001):
    with ExitStack() as stack:
        # Browsers can preconnect without sending an HTTP request immediately.
        for _ in range(4):
            stack.enter_context(socket.create_connection((host, port), timeout=3))
        time.sleep(0.3)
        with urllib.request.urlopen(f"http://{host}:{port}/health/ready", timeout=3) as response:
            assert response.status == 200
    print("Idle browser connections do not block HTTP requests.")


if __name__ == "__main__":
    check()
