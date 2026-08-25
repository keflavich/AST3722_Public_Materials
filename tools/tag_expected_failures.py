#!/usr/bin/env python
"""Mark the cells in an exercise notebook that are meant to raise.

Exercise notebooks ship with cells students fill in -- `result = <your answer
here>`, or a bare `signal = ` -- so running one top to bottom stops at the
first blank. Tagging those cells ``raises-exception`` tells nbclient to record
the traceback and carry on, which is what lets the `executed` branch show an
exercise with everything *except* the blanks worked through.

The tag is per-cell on purpose. Running the whole notebook with allow_errors
would hide a genuine regression just as effectively as it hides the blanks;
tagging says *these* cells are expected to fail, and anything else still stops
the run.

    tag_expected_failures.py                 tag every exercise in the manifest
    tag_expected_failures.py --check         report untagged ones, exit 1
    tag_expected_failures.py --execute NB    also run NB and tag what fails

Two kinds of cell get tagged:

  * Cells that do not compile. A placeholder like `nexp = # implement this` is
    a SyntaxError no matter whose machine it runs on, so this is decided
    statically and is always safe.

  * With --execute, cells that fail at runtime -- almost always a NameError for
    a variable the student was supposed to define. These have to be observed,
    and only in an environment where the notebook's data is present, or a
    missing FITS file would get tagged as if it were a blank.
"""

import argparse
import ast
import sys

import nbtools
from manifest import load_manifest

TAG = "raises-exception"


def cell_tags(cell):
    return cell.setdefault("metadata", {}).setdefault("tags", [])


def is_tagged(cell):
    return TAG in cell.get("metadata", {}).get("tags", [])


def add_tag(cell):
    tags = cell_tags(cell)
    if TAG not in tags:
        tags.append(TAG)
        return True
    return False


def uncompilable_cells(nb):
    """Indices of code cells that are not valid Python (i.e. left blank)."""
    from IPython.core.inputtransformer2 import TransformerManager

    transformer = TransformerManager()
    out = []
    for index, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = nbtools.source_text(cell)
        if not source.strip():
            continue
        try:
            ast.parse(transformer.transform_cell(source))
        except SyntaxError:
            out.append(index)
    return out


def failing_cells(path, timeout=180, workdir=None):
    """Indices of cells that actually raise when the notebook is run."""
    from execute_notebook import execute

    nb, _ = execute(path, timeout=timeout, allow_errors=True, workdir=workdir)
    return sorted({
        index for index, cell in enumerate(nb.cells)
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    })


def tag_notebook(path, extra_indices=()):
    nb = nbtools.load(path)
    wanted = set(uncompilable_cells(nb)) | set(extra_indices)

    added = [i for i in sorted(wanted) if add_tag(nb["cells"][i])]
    if added:
        nbtools.save(nbtools.strip(nb), path)
    return added, sorted(wanted)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="report cells that should be tagged and are not")
    parser.add_argument("--execute", metavar="NOTEBOOK", action="append", default=[],
                        help="run this notebook and tag whatever fails (repeatable)")
    parser.add_argument("--workdir", default=None,
                        help="working directory for --execute runs")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    exercises = manifest.by_status("exercise")

    if args.check:
        problems = []
        for entry in exercises:
            nb = nbtools.load(entry.abspath)
            missing = [i for i in uncompilable_cells(nb)
                       if not is_tagged(nb["cells"][i])]
            if missing:
                problems.append((entry.path, missing))
        if not problems:
            print("{} exercise notebook(s): every unfillable cell is tagged"
                  .format(len(exercises)))
            return 0
        nbtools.eprint("These exercise notebooks have cells that cannot run but "
                       "are not tagged '{}':".format(TAG))
        for path, missing in problems:
            nbtools.eprint("    {}  cells {}".format(path, missing))
        nbtools.eprint("\nTag them with:  python tools/tag_expected_failures.py")
        return 1

    to_execute = {nbtools.relative(p) if "/" in p else p for p in args.execute}
    for entry in exercises:
        extra = ()
        if entry.path in to_execute:
            extra = failing_cells(entry.abspath, workdir=args.workdir)
        added, wanted = tag_notebook(entry.abspath, extra)
        note = " (+{} from running it)".format(len(extra)) if extra else ""
        print("{:<58} {:2d} tagged, {:2d} newly{}".format(
            entry.path, len(wanted), len(added), note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
