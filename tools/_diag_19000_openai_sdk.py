from qclaw_gateway_token import read_gateway_token
"""Test 19000 via OpenAI SDK inside agent exec (historical success path)."""
try:
    from openai import OpenAI
except ImportError:
    print("ERR no openai package")
    raise SystemExit(1)

c = OpenAI(
    base_url="http://127.0.0.1:19000/proxy/llm",
    api_key=read_gateway_token(),
)
try:
    r = c.chat.completions.create(
        model="pool-deepseek-v4-pro",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=50,
        stream=False,
    )
    txt = str(r)[:300]
    print("OK", "reasoning_content" in txt, txt[:200])
except Exception as exc:
    print("FAIL", type(exc).__name__, str(exc)[:300])
