"""Execute inside QClaw gateway process tree - test 19000 payloads."""
import json
from qclaw_gateway_token import read_gateway_token
import urllib.error
import urllib.request

TOKEN = read_gateway_token()
URLS = [
    "http://127.0.0.1:19000/proxy/llm/chat/completions",
    "http://127.0.0.1:19000/proxy/chat/completions",
]
CASES = [
    ("minimal", {"model": "pool-deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 16, "stream": False}),
    ("reasoning_effort", {"model": "pool-deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 16, "stream": False, "reasoning_effort": "low"}),
    ("api-server-style", {"model": "pool-deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50, "temperature": 0.6, "reasoning_effort": "high", "stream": True, "stream_options": {"include_usage": True}}),
    ("adaptive-top", {"model": "pool-deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 16, "stream": False, "thinking": {"type": "adaptive"}, "output_config": {"effort": "low"}}),
    ("deepseek-v4-pro", {"model": "deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 16, "stream": False, "reasoning_effort": "max"}),
]

for url in URLS:
    print(f"URL {url}")
    for name, body in CASES:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TOKEN}",
                "Host": "127.0.0.1:19000",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read(800)
                tag = "REASONING" if b"reasoning_content" in raw else "ok"
                print(f"  {name}: {resp.status} {tag} {raw[:120]!r}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
            print(f"  {name}: HTTP {exc.code} {detail}")
        except Exception as exc:
            print(f"  {name}: ERR {exc}")
    print()
