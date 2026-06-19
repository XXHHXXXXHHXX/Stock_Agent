"""Use QCLAW_LLM_API_KEY from exec environment for 19000."""
import json
from qclaw_gateway_token import read_gateway_token
import os
import urllib.error
import urllib.request

URL = "http://127.0.0.1:19000/proxy/llm/chat/completions"
GW = read_gateway_token()
LLM_KEY = os.environ.get("QCLAW_LLM_API_KEY", "")
print("QCLAW_LLM_API_KEY len=", len(LLM_KEY))
print("QCLAW_LLM_BASE_URL=", os.environ.get("QCLAW_LLM_BASE_URL"))

BODY = {
    "model": "pool-deepseek-v4-pro",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 50,
    "stream": False,
    "reasoning_effort": "high",
}

for label, token in [
    ("llm-env-key", LLM_KEY),
    ("gw-token", GW),
    ("managed", "__QCLAW_AUTH_GATEWAY_MANAGED__"),
]:
    if not token and label == "llm-env-key":
        print(f"{label}: skip (empty)")
        continue
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    req = urllib.request.Request(URL, data=json.dumps(BODY).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read(400)
            tag = "REASONING" if b"reasoning_content" in raw else "ok"
            print(f"{label}: {resp.status} {tag} {raw[:100]!r}")
    except urllib.error.HTTPError as exc:
        print(f"{label}: HTTP {exc.code} {exc.read().decode('utf-8', errors='replace')[:180]}")
