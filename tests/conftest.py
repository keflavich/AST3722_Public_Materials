import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

# Notebooks that plot must not try to open a window on a CI runner.
os.environ.setdefault("MPLBACKEND", "Agg")
