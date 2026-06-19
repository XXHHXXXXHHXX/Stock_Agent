"""Exact payload that worked in tfxjjhfnjialcuju session (2026-06-10)."""
import json
from qclaw_gateway_token import read_gateway_token
import urllib.error
import urllib.request

URL = "http://127.0.0.1:19000/proxy/llm/chat/completions"
TOKEN = read_gateway_token()
BODY = b'{"model": "pool-deepseek-v4-pro", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}'

headers = {
    "Accept-Encoding": "identity",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}",
    "Host": "127.0.0.1:19000",
}
req = urllib.request.Request(URL, data=BODY, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read(800)
        print(f"OK status={resp.status} len={len(raw)} has_reasoning={b'reasoning_content' in raw}")
        print(raw[:200])
except urllib.error.HTTPError as exc:
    print(f"HTTP {exc.code} {exc.read().decode('utf-8', errors='replace')[:300]}")
