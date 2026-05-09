#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
from base64 import b64encode

username = os.getenv("HYDRA_BASIC_USER", "admin")
password = os.getenv("HYDRA_BASIC_PASS", "change-me")
token = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")

REQUEST = urllib.request.Request(
    "http://localhost:8000/opportunities/mock-scan",
    headers={"Authorization": f"Basic {token}"},
    method="POST",
)

with urllib.request.urlopen(REQUEST, timeout=20) as response:
    payload = json.loads(response.read().decode("utf-8"))

print(json.dumps(payload, indent=2))
