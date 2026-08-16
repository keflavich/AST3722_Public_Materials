"""Shared helpers for the notebook tooling.

Deliberately dependency-free (stdlib only) so that the git filter and the
git hooks keep working in whatever interpreter happens to be on PATH.
"""

import copy
import json
import os
import sys

# Notebook-level metadata that records *how* a notebook was run rather than
# what it says.  Dropping it keeps diffs from churning every time a notebook is
# opened in a different environment.
VOLATILE_NOTEBOOK_METADATA = (
    "signature",
    "widgets",
)

# Cell-level metadata in the same category.
VOLATILE_CELL_METADATA = (
    "collapsed",
    "execution",
    "scrolled",
    "ExecuteTime",
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dumps(nb):
    """Serialize a notebook the way Jupyter itself does.

    Matching Jupyter's formatting (2-space indent, trailing newline, no
    trailing whitespace on lines) means saving a notebook in the browser does
    not produce a whole-file diff.
    """
    text = json.dumps(nb, indent=1, sort_keys=True, ensure_ascii=False)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text + "\n"


def save(nb, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dumps(nb))


def normalize_kernelspec(nb):
    """Point a Python notebook at the stock ``python3`` kernel.

    Notebooks saved from a personal conda environment record its name --
    "py39", "26a_3722real" -- and then fail to open for anyone else with
    "No such kernel". Which environment you happened to use is not part of the
    lesson, so it does not belong in the file.

    Non-Python kernels are left alone. Returns True if anything changed.
    """
    kernelspec = nb.setdefault("metadata", {}).get("kernelspec")
    if not kernelspec:
        return False
    if kernelspec.get("language", "python") != "python":
        return False
    if kernelspec.get("name") == "python3":
        return False
    kernelspec["name"] = "python3"
    kernelspec["display_name"] = "Python 3"
    return True


def strip(nb):
    """Return a copy of ``nb`` with all execution results removed.

    Removes cell outputs, execution counts, and the environment-dependent
    metadata that otherwise makes notebook diffs unreadable -- including the
    name of whichever conda environment the notebook was last run in.
    language_info is kept: it describes what the notebook needs, not what
    happened when it was run.
    """
    nb = copy.deepcopy(nb)

    metadata = nb.get("metadata", {})
    for key in VOLATILE_NOTEBOOK_METADATA:
        metadata.pop(key, None)
    normalize_kernelspec(nb)

    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        cell_metadata = cell.get("metadata", {})
        for key in VOLATILE_CELL_METADATA:
            cell_metadata.pop(key, None)
        # An id is required by nbformat 4.5+ but is not meaningful content;
        # leave it alone if present rather than churning it.

    return nb


def has_outputs(nb):
    """True if any cell carries execution results."""
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs"):
            return True
        if cell.get("execution_count") is not None:
            return True
    return False


def describe_dirt(nb):
    """List the reasons this notebook is not in the form we commit.

    Broader than has_outputs: a notebook can be free of outputs and still name
    a personal conda environment as its kernel, or carry per-run cell metadata.
    Returns a list of short human-readable strings, empty if the notebook is
    clean.
    """
    reasons = []
    if has_outputs(nb):
        reasons.append("execution results")

    kernelspec = nb.get("metadata", {}).get("kernelspec", {})
    if (kernelspec.get("language", "python") == "python"
            and kernelspec.get("name") not in (None, "python3")):
        reasons.append("kernel {!r}".format(kernelspec.get("name")))

    if any(k in nb.get("metadata", {}) for k in VOLATILE_NOTEBOOK_METADATA):
        reasons.append("run-specific notebook metadata")

    if any(k in cell.get("metadata", {})
           for cell in nb.get("cells", [])
           for k in VOLATILE_CELL_METADATA):
        reasons.append("run-specific cell metadata")

    return reasons


def source_text(cell):
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return source


def graft_outputs(stripped, executed):
    """Carry outputs from ``executed`` onto ``stripped``.

    Cells are matched by source text, in order, so that inserting, deleting, or
    reordering cells does not attach one cell's output to another's code.  A
    cell whose source changed since the last execution comes back empty -- a
    missing plot is recoverable, a plot that no longer matches its code is a
    lie.

    Returns ``(notebook, n_grafted)``.
    """
    result = copy.deepcopy(stripped)

    # Bucket the executed cells by source text, preserving order within each
    # bucket so repeated identical cells (common in these notebooks) map
    # first-to-first.
    available = {}
    for cell in executed.get("cells", []):
        if cell.get("cell_type") != "code" or not cell.get("outputs"):
            continue
        available.setdefault(source_text(cell), []).append(cell)

    grafted = 0
    for cell in result.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        matches = available.get(source_text(cell))
        if not matches:
            continue
        donor = matches.pop(0)
        cell["outputs"] = copy.deepcopy(donor.get("outputs", []))
        cell["execution_count"] = donor.get("execution_count")
        grafted += 1

    return result, grafted


def iter_notebooks(root=REPO_ROOT):
    """Yield every notebook in the repo, skipping checkpoints."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in (".git", ".ipynb_checkpoints", "__pycache__")
        ]
        for name in sorted(filenames):
            if name.endswith(".ipynb"):
                yield os.path.join(dirpath, name)


def relative(path, root=REPO_ROOT):
    return os.path.relpath(path, root)


def eprint(*args):
    print(*args, file=sys.stderr)
