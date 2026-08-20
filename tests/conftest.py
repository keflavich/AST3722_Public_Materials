import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))

# Deliberately NOT setting MPLBACKEND=Agg here.
#
# A Jupyter kernel defaults to the matplotlib_inline backend, which is both
# headless-safe and the thing that captures figures as cell outputs. Forcing
# Agg overrides it: the notebooks still run, but every plot is silently
# discarded, so the `executed` branch ends up with no pictures in it. If you
# need to suppress a GUI somewhere, do it in that process, not here.
