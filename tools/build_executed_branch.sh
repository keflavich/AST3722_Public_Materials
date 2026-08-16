#!/bin/sh
# Rebuild the `executed` branch from the stripped sources on `master`.
#
# Usage (from anywhere):
#     tools/build_executed_branch.sh <stripped-checkout> <executed-checkout>
#
# `executed` is a mirror of `master` in which the notebooks carry outputs, so
# that nbviewer and the RISE slide links show plots.  It is machine-generated;
# never edit it by hand, your changes get overwritten on the next build.
#
# How a notebook gets its outputs:
#
#   * Notebooks the manifest marks `run` or `network` are executed here, so
#     their outputs are freshly generated and match the code above them.
#   * Everything else -- the notebooks that need telescope data nobody has in
#     CI, and the exercises that raise by design -- keeps whatever outputs the
#     `executed` branch already had, cell by cell, matched on source text.
#     An edited cell loses its old output rather than showing a plot that no
#     longer corresponds to its code.

set -e

stripped=$1
executed=$2

if [ -z "$stripped" ] || [ -z "$executed" ]; then
    echo "usage: $0 <stripped-checkout> <executed-checkout>" >&2
    exit 2
fi

stripped=$(cd "$stripped" && pwd)
executed=$(cd "$executed" && pwd)
previous="${executed}.previous"

python=${PYTHON:-python3}

echo "=== Keeping a copy of the current executed branch"
rm -rf "$previous"
cp -R "$executed" "$previous"
rm -rf "$previous/.git"

echo "=== Copying sources from the stripped branch"
# Everything from master except its git metadata and the filter config, which
# would strip the very outputs this branch exists to carry.
rsync -a --delete \
      --exclude '.git/' \
      --exclude '.gitattributes' \
      "$stripped/" "$executed/"
rm -f "$executed/.gitattributes"

cat > "$executed/EXECUTED_BRANCH.md" <<'EOF'
# This branch is generated

`executed` is a build artifact: it is `master` with the notebooks run, so that
nbviewer and the RISE slide links show plots and tables.

**Do not commit here.** Every build of
[`.github/workflows/build-executed.yml`](.github/workflows/build-executed.yml)
overwrites this branch from `master`. Make your changes on `master`, where the
notebooks are stripped and the diffs are readable.

Notebooks marked `run` or `network` in `notebooks.toml` were executed by CI.
The rest carry outputs preserved from earlier commits -- they need observing
data that isn't in this repository, or they are exercises with cells left
blank for students, so no machine can run them unattended.
EOF

echo "=== Executing the notebooks CI can run"
# Run in a scratch copy rather than in the checkout: DirectoryStructure.ipynb
# and MachineReadableTables.ipynb write files as they go (new_directory/,
# table.fits, ...), and those would otherwise be swept into the commit by
# `git add -A`.  Only the notebooks come back.
scratch="${executed}.workdir"
rm -rf "$scratch"
cp -R "$executed" "$scratch"
rm -rf "$scratch/.git"

cd "$scratch"
# A notebook that fails is left un-executed; the graft step below then restores
# whatever outputs it had before.  An upstream outage should not empty out the
# branch.
"$python" tools/execute_notebook.py \
    --status run --status network --in-place --keep-going || \
    echo "(some notebooks failed to execute; keeping their previous outputs)"

echo "=== Collecting the executed notebooks"
cd "$scratch"
find . -name '*.ipynb' -not -path './.ipynb_checkpoints/*' -print | while IFS= read -r nb; do
    mkdir -p "$executed/$(dirname "$nb")"
    cp "$nb" "$executed/$nb"
done

echo "=== Carrying over outputs for the notebooks CI cannot run"
cd "$executed"
"$python" tools/graft_outputs.py --from-dir "$previous" --into-dir "$executed"

echo "=== Done"
