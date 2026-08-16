#!/usr/bin/env python
"""Remove execution results from notebooks.

Three ways to call it:

    strip_outputs.py --filter < notebook.ipynb > stripped.ipynb
        Reads one notebook on stdin and writes it stripped to stdout.  This is
        the mode git uses; see .gitattributes and tools/install_hooks.sh.

    strip_outputs.py notebook.ipynb [more.ipynb ...]
        Strips the named notebooks in place.  With no arguments, strips every
        notebook in the repository.

    strip_outputs.py --check [notebook.ipynb ...]
        Reports notebooks that still carry outputs and exits 1 if any do.
        Used by the git hooks and by CI.
"""

import argparse
import json
import sys

import nbtools


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("notebooks", nargs="*",
                        help="notebooks to process (default: all in the repo)")
    parser.add_argument("--filter", action="store_true",
                        help="read one notebook on stdin, write it to stdout")
    parser.add_argument("--check", action="store_true",
                        help="report notebooks with outputs instead of stripping them")
    args = parser.parse_args(argv)

    if args.filter:
        return run_filter()

    paths = args.notebooks or list(nbtools.iter_notebooks())

    if args.check:
        return run_check(paths)

    changed = 0
    for path in paths:
        nb = nbtools.load(path)
        reasons = nbtools.describe_dirt(nb)
        if not reasons:
            continue
        nbtools.save(nbtools.strip(nb), path)
        print("stripped {} ({})".format(nbtools.relative(path), ", ".join(reasons)))
        changed += 1
    print("{} notebook(s) stripped, {} already clean".format(changed, len(paths) - changed))
    return 0


def run_filter():
    """Git clean-filter mode: stdin to stdout, and never lose data.

    A filter that raises makes ``git add`` fail, so anything unparseable is
    passed through untouched rather than blowing up the commit.
    """
    raw = sys.stdin.read()
    try:
        nb = json.loads(raw)
        out = nbtools.dumps(nbtools.strip(nb))
    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        nbtools.eprint("strip_outputs: passing notebook through unchanged ({})".format(exc))
        out = raw
    sys.stdout.write(out)
    return 0


def run_check(paths):
    dirty = []
    for path in paths:
        reasons = nbtools.describe_dirt(nbtools.load(path))
        if reasons:
            dirty.append((path, reasons))

    if not dirty:
        print("{} notebook(s) checked, all clean".format(len(paths)))
        return 0

    nbtools.eprint("These notebooks are not in the form this branch commits:")
    for path, reasons in dirty:
        nbtools.eprint("    {}  ({})".format(nbtools.relative(path), ", ".join(reasons)))
    nbtools.eprint("")
    nbtools.eprint("Fix them with:  python tools/strip_outputs.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
