"""Full payload matrix matching historical successful tests."""
import json
from qclaw_gateway_token import read_gateway_token
import urllib.error
import urllib.request

URL = "http://127.0.0.1:19000/proxy/llm/chat/completions"
TOKEN = read_gateway_token()

CASES = [
    ("hist-stream-full", {
        "model": "pool-deepseek-v4-pro",
        "messages": [{"role": "user", "content": "hi"}],
        "stream": True,
        "max_tokens": 524288,
        "reasoning_effort": "max",
        "stream_options": {"include_usage": True},
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "max"},
    }),
    ("hist-nonstream", {
        "model": "pool-deepseek-v4-pro",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 50,
        "stream": False,
    }),
    ("api-server-style", {
        "model": "pool-deepseek-v4-pro",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 50,
        "temperature": 0.6,
        "reasoning_effort": "max",
        "stream": False,
    }),
]

for name, body in CASES:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
        "Host": "127.0.0.1:19000",
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read(500)
            tag = "REASONING" if b"reasoning_content" in raw else "ok"
            print(f"{name}: {resp.status} {tag} len={len(raw)}")
    except urllib.error.HTTPError as exc:
        print(f"{name}: HTTP {exc.code} {exc.read().decode('utf-8', errors='replace')[:200]}")
    except Exception as exc:
        print(f"{name}: ERR {exc}")
