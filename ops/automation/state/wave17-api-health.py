#!/usr/bin/env python3
"""Wave-17 API health check v3: load DEEPSEEK key from ~/.hermes/.env,
make ONE trivial API call, print only the HTTP status. Never prints the key."""
import json
import pathlib
import sys
import urllib.request

ENV_FILE = pathlib.Path.home() / ".hermes" / ".env"

def load_env_keys():
    keys = {}
    if not ENV_FILE.exists():
        return keys
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        keys[k.strip()] = v.strip().strip("'").strip('"')
    return keys

env = load_env_keys()
key = env.get("DEEPSEEK_API_KEY") or env.get("DEEPSEEK_API_TOKEN")
if not key:
    print("HEALTH: no DEEPSEEK key in ~/.hermes/.env")
    sys.exit(3)
print(f"HEALTH: key found in ~/.hermes/.env (len={len(key)})")

body = json.dumps({
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 1,
    "stream": False,
}).encode()
req = urllib.request.Request(
    "https://api.deepseek.com/chat/completions",
    data=body,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"HEALTH: HTTP {resp.status}")
        if resp.status == 200:
            print("HEALTH: OK - fan-out allowed")
            sys.exit(0)
        sys.exit(1)
except urllib.error.HTTPError as e:
    print(f"HEALTH: HTTP {e.code}")
    sys.exit(1 if e.code in (429, 402) else 2)
except Exception as e:
    print(f"HEALTH: ERROR {e}")
    sys.exit(2)
