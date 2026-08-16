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
