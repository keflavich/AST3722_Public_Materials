"""Tests for the course notebooks.

Two kinds of test live here:

* Structural checks, which run everywhere and are fast -- the manifest matches
  what is on disk, every notebook is valid nbformat, and the notebooks we
  claim to run don't contain fill-in-the-blank cells.

* Execution tests, which actually run notebooks end to end.  Notebooks marked
  ``network`` in the manifest are deselected by default (see pytest.ini); run
  them with ``pytest -m network``.
"""

import ast
import os

import pytest

import nbtools
from manifest import STATUSES, load_manifest

MANIFEST = load_manifest()


def ids(entries):
    return [e.path for e in entries]


# --------------------------------------------------------------------------
# The manifest describes reality
# --------------------------------------------------------------------------

def test_manifest_lists_every_notebook():
    on_disk = {nbtools.relative(p) for p in nbtools.iter_notebooks()}
    listed = MANIFEST.paths

    missing = sorted(on_disk - listed)
    assert not missing, (
        "These notebooks are not in notebooks.toml, so nothing tests them:\n  "
        + "\n  ".join(missing)
        + "\n\nAdd each one under [run], [network], [needs-data], or [exercise]."
    )


def test_manifest_has_no_ghosts():
    on_disk = {nbtools.relative(p) for p in nbtools.iter_notebooks()}
    stale = sorted(MANIFEST.paths - on_disk)
    assert not stale, (
        "notebooks.toml lists notebooks that no longer exist:\n  "
        + "\n  ".join(stale)
    )


def test_manifest_statuses_are_known():
    assert all(e.status in STATUSES for e in MANIFEST.entries)


# --------------------------------------------------------------------------
# Every notebook, regardless of whether we can run it
# --------------------------------------------------------------------------

@pytest.mark.parametrize("entry", MANIFEST.entries, ids=ids(MANIFEST.entries))
def test_notebook_is_valid(entry):
    """The file parses as a notebook and nbformat is happy with it."""
    import nbformat

    with open(entry.abspath, encoding="utf-8") as fh:
        nb = nbformat.read(fh, as_version=4)
    nbformat.validate(nb)
    assert nb.cells, "{} has no cells".format(entry.path)


@pytest.mark.parametrize("entry", MANIFEST.entries, ids=ids(MANIFEST.entries))
def test_notebook_opens_on_a_stock_kernel(entry):
    """A notebook that names someone's conda env won't open for anyone else.

    Jupyter records the kernel a notebook was last run in, so a save from
    "26a_3722real" or "py39" leaves every student -- and CI -- with "No such
    kernel". strip_outputs.py rewrites these to python3; this catches any that
    got in another way.
    """
    nb = nbtools.load(entry.abspath)
    kernelspec = nb.get("metadata", {}).get("kernelspec", {})
    language = kernelspec.get("language", "python")
    assert language == "python", (
        "{} declares a {} kernel".format(entry.path, language)
    )
    assert kernelspec.get("name", "python3") == "python3", (
        "{} wants the kernel {!r}, which exists only on the machine it was "
        "saved from. Run: python tools/strip_outputs.py".format(
            entry.path, kernelspec.get("name"))
    )


# --------------------------------------------------------------------------
# Notebooks we claim to be runnable had better not be exercises
# --------------------------------------------------------------------------

def compilable_cells(path):
    """Yield (index, source, error) for code cells that don't compile.

    IPython syntax (``%magic``, ``!shell``, ``plot?``) is translated first, so
    only genuinely broken Python -- which in this repo means a fill-in-the-blank
    placeholder -- shows up.
    """
    from IPython.core.inputtransformer2 import TransformerManager

    transformer = TransformerManager()
    nb = nbtools.load(path)
    for index, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = nbtools.source_text(cell)
        if not source.strip():
            continue
        try:
            ast.parse(transformer.transform_cell(source))
        except SyntaxError as exc:
            yield index, source, exc


RUNNABLE = MANIFEST.by_status("run", "network")


@pytest.mark.parametrize("entry", RUNNABLE, ids=ids(RUNNABLE))
def test_runnable_notebooks_have_no_placeholders(entry):
    """A 'run' or 'network' notebook is an answer key: all its code compiles."""
    broken = list(compilable_cells(entry.abspath))
    assert not broken, (
        "{} is marked '{}' but has cells that aren't valid Python:\n  ".format(
            entry.path, entry.status)
        + "\n  ".join("cell {}: {!r}".format(i, s.strip()[:70]) for i, s, _ in broken)
        + "\n\nEither finish those cells or move the notebook to [exercise]."
    )


EXERCISES = MANIFEST.by_status("exercise")


@pytest.mark.parametrize("entry", EXERCISES, ids=ids(EXERCISES))
def test_exercises_actually_have_blanks(entry):
    """Guards the other direction: a finished notebook shouldn't sit in [exercise].

    Blank code cells count as blanks too -- plenty of these exercises leave an
    empty cell for the student rather than a broken one.
    """
    nb = nbtools.load(entry.abspath)
    blank_cells = sum(
        1 for c in nb.get("cells", [])
        if c.get("cell_type") == "code" and not nbtools.source_text(c).strip()
    )
    placeholders = len(list(compilable_cells(entry.abspath)))
    assert blank_cells or placeholders, (
        "{} is marked [exercise] but every cell is filled in. If it runs, move "
        "it to [run] or [network] so the suite covers it.".format(entry.path)
    )


# --------------------------------------------------------------------------
# End-to-end execution
# --------------------------------------------------------------------------

def run_notebook(entry, workdir):
    from execute_notebook import describe_failure, execute

    # Run in a scratch directory: DirectoryStructure.ipynb and
    # MachineReadableTables.ipynb write files as they go, and a test suite
    # should not leave debris in the repository.
    nb, exc = execute(entry.abspath,
                      timeout=MANIFEST.cell_timeout,
                      allow_errors=entry.allow_errors,
                      workdir=str(workdir))
    if exc is not None:
        pytest.fail("{} failed to execute: {}".format(entry.path, describe_failure(exc)),
                    pytrace=False)

    if entry.allow_errors:
        return

    # allow_errors=False already aborts on the first traceback, but a cell can
    # also report an error without raising (e.g. a %%capture'd one).
    for index, cell in enumerate(nb.cells):
        for output in cell.get("outputs", []):
            assert output.get("output_type") != "error", (
                "{} cell {} produced {}: {}".format(
                    entry.path, index,
                    output.get("ename"), output.get("evalue"))
            )


OFFLINE = MANIFEST.by_status("run")


@pytest.mark.parametrize("entry", OFFLINE, ids=ids(OFFLINE))
def test_notebook_executes(entry, tmp_path):
    run_notebook(entry, tmp_path)


ONLINE = MANIFEST.by_status("network")


@pytest.mark.network
@pytest.mark.parametrize("entry", ONLINE, ids=ids(ONLINE))
def test_notebook_executes_with_network(entry, tmp_path):
    run_notebook(entry, tmp_path)


# --------------------------------------------------------------------------
# Nothing here is executed, but it should at least be openable
# --------------------------------------------------------------------------

SKIPPED = MANIFEST.by_status("needs-data", "exercise")


@pytest.mark.parametrize("entry", SKIPPED, ids=ids(SKIPPED))
def test_unexecuted_notebook_exists(entry):
    assert os.path.exists(entry.abspath), (
        "{} is in the manifest but not on disk".format(entry.path))
