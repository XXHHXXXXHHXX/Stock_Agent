"""Execute inside QClaw gateway - test modelroute and auth variants."""
import json
from qclaw_gateway_token import read_gateway_token
import urllib.error
import urllib.request

TOKEN = read_gateway_token()
URL = "http://127.0.0.1:19000/proxy/llm/chat/completions"

CASES = [
    ("modelroute-minimal", {"model": "modelroute", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 16, "stream": False}),
    ("modelroute-reasoning", {"model": "modelroute", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50, "stream": False, "reasoning_effort": "max"}),
    ("modelroute-stream", {"model": "modelroute", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50, "stream": True, "reasoning_effort": "high"}),
    ("pool-no-auth", {"model": "pool-deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 16, "stream": False}),
]

for name, body in CASES:
    headers = {"Content-Type": "application/json", "Host": "127.0.0.1:19000"}
    if "no-auth" not in name:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(800)
            tag = "REASONING" if b"reasoning_content" in raw else "ok"
            print(f"{name}: {resp.status} {tag} {raw[:150]!r}")
    except urllib.error.HTTPError as exc:
        print(f"{name}: HTTP {exc.code} {exc.read().decode('utf-8', errors='replace')[:200]}")
    except Exception as exc:
        print(f"{name}: ERR {exc}")
