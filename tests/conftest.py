import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

# Keep stray plots from opening windows on whoever is running the tests.
#
# This applies to the pytest process only. Notebook kernels get the inline
# backend regardless of what is set here -- tools/execute_notebook.py pins it
# when it starts them -- because Agg would run the notebooks fine while
# silently discarding every figure they draw.
os.environ.setdefault("MPLBACKEND", "Agg")
