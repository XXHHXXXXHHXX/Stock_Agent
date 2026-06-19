"""Compare auth tokens and payload shapes for 19000."""
import json
from qclaw_gateway_token import read_gateway_token
import urllib.error
import urllib.request

URL = "http://127.0.0.1:19000/proxy/llm/chat/completions"
GW_TOKEN = read_gateway_token()
MANAGED = "__QCLAW_AUTH_GATEWAY_MANAGED__"

BODY = {
    "model": "pool-deepseek-v4-pro",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 50,
    "stream": False,
    "reasoning_effort": "high",
}

for label, token, extra_hdr in [
    ("gw-token+host", GW_TOKEN, {"Host": "127.0.0.1:19000"}),
    ("gw-token-no-host", GW_TOKEN, {}),
    ("managed+host", MANAGED, {"Host": "127.0.0.1:19000"}),
    ("managed-no-host", MANAGED, {}),
]:
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}", **extra_hdr}
    req = urllib.request.Request(URL, data=json.dumps(BODY).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(300)
            tag = "REASONING" if b"reasoning_content" in raw else "ok"
            print(f"{label}: {resp.status} {tag} {raw[:120]!r}")
    except urllib.error.HTTPError as exc:
        print(f"{label}: HTTP {exc.code} {exc.read().decode('utf-8', errors='replace')[:180]}")
    except Exception as exc:
        print(f"{label}: ERR {exc}")
