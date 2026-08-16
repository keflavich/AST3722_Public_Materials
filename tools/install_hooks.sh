#!/bin/sh
# One-time setup for a fresh clone.  Safe to re-run.
#
# Sets up two things:
#
#  1. A git "clean" filter, so that notebook outputs are stripped as they are
#     staged.  You keep your plots on screen; git records only the code and
#     prose.  .gitattributes points *.ipynb at this filter, but the filter
#     itself has to be defined per-clone -- git will not run a program named
#     by a file it just downloaded, which is why this script exists.
#
#  2. The pre-commit and post-commit hooks, which catch anything the filter
#     misses (and tell you when the filter isn't doing its job).

set -e

root=$(git rev-parse --show-toplevel)
cd "$root"

python=${PYTHON:-python3}
if ! command -v "$python" >/dev/null 2>&1; then
    python=python
fi
if ! command -v "$python" >/dev/null 2>&1; then
    echo "install_hooks.sh: no python on PATH; set PYTHON=/path/to/python and re-run" >&2
    exit 1
fi

echo "Using $python ($("$python" --version 2>&1))"

# 1. The clean filter.  No smudge filter: on checkout the file is written as
#    stored, i.e. stripped, which is what we want.
git config filter.strip_outputs.clean "$python \"$root/tools/strip_outputs.py\" --filter"
git config --unset filter.strip_outputs.smudge 2>/dev/null || true
echo "Configured filter.strip_outputs.clean"

# 2. The hooks.  Symlink where we can so that edits to tools/hooks take effect
#    without re-running this script; copy where symlinks are awkward.
hooks_dir=$(git rev-parse --git-path hooks)
mkdir -p "$hooks_dir"
for hook in pre-commit post-commit; do
    src="$root/tools/hooks/$hook"
    dst="$hooks_dir/$hook"
    chmod +x "$src"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        echo "  $hook already exists and is not a symlink; saving it as $hook.local" >&2
        mv "$dst" "$dst.local"
    fi
    rm -f "$dst"
    ln -s "$src" "$dst" 2>/dev/null || cp "$src" "$dst"
    chmod +x "$dst"
    echo "Installed $hook"
done

# Re-stage nothing, but tell the user where they stand.
echo
if "$python" "$root/tools/strip_outputs.py" --check >/dev/null 2>&1; then
    echo "All notebooks in the working tree are already stripped."
else
    echo "Note: some notebooks in your working tree carry outputs. That is fine --"
    echo "they will be stripped on the way into a commit. To strip them on disk too:"
    echo
    echo "    $python tools/strip_outputs.py"
fi
echo
echo "Done."
