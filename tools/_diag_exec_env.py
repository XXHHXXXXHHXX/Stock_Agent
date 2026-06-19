import os
print("QCLAW_LLM_BASE_URL=", os.environ.get("QCLAW_LLM_BASE_URL"))
print("QCLAW_LLM_API_KEY=", "set" if os.environ.get("QCLAW_LLM_API_KEY") else "missing")
print("PPID=", os.getppid())
print("PID=", os.getpid())
