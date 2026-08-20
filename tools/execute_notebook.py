#!/usr/bin/env python
"""Execute notebooks end to end.

    execute_notebook.py "SNR Investigation Continued.ipynb"
        Run one notebook and report whether it finished.

    execute_notebook.py --status run --status network --in-place
        Run every notebook the manifest gives those statuses and save the
        results back into the files.  This is how the `executed` branch is
        rebuilt.

Notebooks run with their own directory as the working directory, so the
relative paths inside them ("data_mar8_2021/...") mean what they mean when you
open the notebook by hand.
"""

import argparse
import contextlib
import os
import sys
import traceback

import nbtools
from manifest import load_manifest

# The backend a Jupyter kernel uses by default. It draws to an in-memory PNG
# that gets attached to the cell as output, and it never opens a window.
INLINE_BACKEND = "module://matplotlib_inline.backend_inline"


@contextlib.contextmanager
def inline_backend():
    """Pin MPLBACKEND to the inline backend for any kernel started inside.

    A kernel inherits this process's environment, so an ambient
    MPLBACKEND=Agg -- which a test suite quite reasonably sets, to stop stray
    plots opening windows on someone's laptop -- would silently follow it in
    and throw away every figure the notebooks draw. The notebooks would still
    pass; they would just come back with no pictures in them.

    Agg and the inline backend both avoid opening windows. Only the inline one
    also captures what was drawn, so that is what notebook execution gets,
    whatever the caller happens to have set.
    """
    previous = os.environ.get("MPLBACKEND")
    os.environ["MPLBACKEND"] = INLINE_BACKEND
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("MPLBACKEND", None)
        else:
            os.environ["MPLBACKEND"] = previous


def execute(path, timeout=600, kernel_name=None, allow_errors=False, workdir=None):
    """Run a notebook.  Returns ``(executed_notebook, error_or_None)``.

    ``workdir`` is the kernel's working directory; it defaults to the
    notebook's own directory so that relative paths inside the notebook mean
    what they mean when you open it by hand.  Tests override it with a scratch
    directory, since a few of these notebooks write files as they run.

    ``kernel_name`` defaults to the stock ``python3`` kernel rather than to
    whatever the notebook's metadata names.  The point of the test matrix is to
    find out whether these notebooks work on a given Python, so they have to
    run on the interpreter under test -- and a notebook saved from a personal
    conda environment names a kernel that exists on exactly one machine.
    """
    import nbformat
    from nbclient import NotebookClient

    with open(path, encoding="utf-8") as fh:
        nb = nbformat.read(fh, as_version=4)

    client = NotebookClient(
        nb,
        timeout=timeout,
        kernel_name=kernel_name or "python3",
        allow_errors=allow_errors,
        resources={"metadata": {"path": workdir or os.path.dirname(os.path.abspath(path))}},
        # These notebooks are teaching material; a stray missing font or an
        # astropy deprecation warning on stderr is not a failure.
        record_timing=False,
    )

    try:
        # The kernel picks up MPLBACKEND when it starts, so the whole run has
        # to happen inside this.
        with inline_backend():
            client.execute()
    except Exception as exc:  # noqa: BLE001 - the failure is the result here
        return nb, exc
    return nb, None


def describe_failure(exc):
    """A short, greppable summary of why a notebook died."""
    from nbclient.exceptions import CellExecutionError, CellTimeoutError

    if isinstance(exc, CellTimeoutError):
        return "timed out"
    if isinstance(exc, CellExecutionError):
        # CellExecutionError's str() is the whole traceback; the last
        # non-empty line is the actual exception.
        lines = [line.strip() for line in str(exc).splitlines() if line.strip()]
        return lines[-1] if lines else "cell execution failed"
    return "{}: {}".format(type(exc).__name__, exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("notebooks", nargs="*", help="notebooks to run")
    parser.add_argument("--status", action="append", default=[],
                        help="run every notebook with this manifest status (repeatable)")
    parser.add_argument("--in-place", action="store_true",
                        help="write the executed notebook back to disk")
    parser.add_argument("--timeout", type=int, default=600,
                        help="per-cell timeout in seconds (default: 600)")
    parser.add_argument("--kernel", default=None,
                        help="kernel to run in (default: python3, i.e. the "
                             "interpreter this script is running under)")
    parser.add_argument("--keep-going", action="store_true",
                        help="run every notebook even after one fails")
    args = parser.parse_args(argv)

    paths = list(args.notebooks)
    allow_errors = set()
    if args.status:
        manifest = load_manifest()
        for entry in manifest.by_status(*args.status):
            paths.append(entry.abspath)
            if entry.allow_errors:
                allow_errors.add(entry.abspath)
    if not paths:
        parser.error("give notebook paths, or --status")

    failures = []
    for path in paths:
        rel = nbtools.relative(os.path.abspath(path))
        print("=== {}".format(rel), flush=True)
        try:
            nb, exc = execute(path, timeout=args.timeout,
                              kernel_name=args.kernel,
                              allow_errors=os.path.abspath(path) in allow_errors)
        except Exception:  # noqa: BLE001 - setup problems, e.g. no kernel
            traceback.print_exc()
            failures.append((rel, "could not start"))
            if not args.keep_going:
                break
            continue

        if exc is None:
            print("    ok", flush=True)
            if args.in_place:
                import nbformat
                with open(path, "w", encoding="utf-8") as fh:
                    nbformat.write(nb, fh)
        else:
            reason = describe_failure(exc)
            print("    FAILED: {}".format(reason), flush=True)
            failures.append((rel, reason))
            if not args.keep_going:
                break

    if failures:
        print("\n{} of {} notebook(s) failed:".format(len(failures), len(paths)))
        for rel, reason in failures:
            print("    {}: {}".format(rel, reason))
        return 1

    print("\nall {} notebook(s) ran to completion".format(len(paths)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
