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


def strip(nb):
    """Return a copy of ``nb`` with all execution results removed.

    Removes cell outputs, execution counts, and the environment-dependent
    metadata that otherwise makes notebook diffs unreadable.  The kernelspec
    and language_info are kept: they describe what the notebook needs, not what
    happened when it was run.
    """
    nb = copy.deepcopy(nb)

    metadata = nb.get("metadata", {})
    for key in VOLATILE_NOTEBOOK_METADATA:
        metadata.pop(key, None)

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
