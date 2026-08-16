#!/usr/bin/env python
"""Copy execution results from one copy of a notebook onto another.

Used when rebuilding the `executed` branch: the sources come from the stripped
branch, and outputs come from whatever the `executed` branch already had, so
that notebooks nobody can run in CI (they need telescope data or a network
service) keep the outputs they were committed with.

    graft_outputs.py --from-dir old_executed_checkout --into-dir .

Only cells whose source is byte-for-byte unchanged inherit their old outputs.
Edited cells come back empty rather than showing a plot that no longer
corresponds to the code above it.
"""

import argparse
import os
import sys

import nbtools


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-dir", required=True,
                        help="checkout holding the previously-executed notebooks")
    parser.add_argument("--into-dir", default=".",
                        help="checkout holding the stripped notebooks to fill in")
    args = parser.parse_args(argv)

    total_cells = 0
    total_notebooks = 0

    for path in nbtools.iter_notebooks(args.into_dir):
        rel = os.path.relpath(path, args.into_dir)
        donor_path = os.path.join(args.from_dir, rel)
        if not os.path.exists(donor_path):
            print("no previous outputs for {}".format(rel))
            continue

        target = nbtools.load(path)
        if nbtools.has_outputs(target):
            # Already executed in this run; leave the fresh outputs alone.
            continue

        try:
            donor = nbtools.load(donor_path)
        except ValueError as exc:
            nbtools.eprint("skipping {}: donor is not readable ({})".format(rel, exc))
            continue

        merged, count = nbtools.graft_outputs(target, donor)
        if count:
            nbtools.save(merged, path)
            total_cells += count
            total_notebooks += 1
            print("{}: carried over {} cell output(s)".format(rel, count))
        else:
            print("{}: nothing to carry over".format(rel))

    print("grafted outputs onto {} notebook(s), {} cell(s) total"
          .format(total_notebooks, total_cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
