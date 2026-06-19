"""直接运行此文件启动 PA Agent。

用法：
    python run.py

或者双击 run.py（如果系统关联了 Python）。
"""
import sys
import os

# 确保 PA_Agent 目录在 sys.path 里（当从其他目录运行时也能找到包）
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from pa_agent.main import main

if __name__ == "__main__":
    raise SystemExit(main())
