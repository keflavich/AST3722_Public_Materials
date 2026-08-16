"""Reader for notebooks.toml, the per-notebook test manifest.

Every notebook in the repository must appear in the manifest with one of the
statuses below; ``tests/test_notebooks.py`` fails if one is missing, so a new
notebook cannot silently escape the test suite.

    run         Executes unattended with only the packages in
                requirements.txt.  CI runs these on every supported Python and
                a failure blocks the build.
    network     Executes, but queries a remote service (SESAME, SIMBAD,
                VizieR, SkyView).  Run in a separate CI job that is allowed to
                fail, since an outage upstream is not a bug here.
    needs-data  Reads observing data that does not live in this repository.
                Not executed; checked for structural validity only.
    exercise    Has cells students are meant to fill in, so it raises by
                design.  Not executed; checked for structural validity only.
"""

import os
import sys

import nbtools

STATUSES = ("run", "network", "needs-data", "exercise")
MANIFEST_PATH = os.path.join(nbtools.REPO_ROOT, "notebooks.toml")


def _load_toml(path):
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover - only on 3.10 and older
        try:
            import tomli as tomllib
        except ImportError:
            raise SystemExit(
                "Reading {} needs Python 3.11+ (for tomllib) or the 'tomli' "
                "package on older interpreters:  pip install tomli"
                .format(os.path.basename(path))
            )
    with open(path, "rb") as fh:
        return tomllib.load(fh)


class Entry(object):
    def __init__(self, path, status, reason="", allow_errors=False):
        self.path = path
        self.status = status
        self.reason = reason
        # Some notebooks raise on purpose -- DirectoryStructure.ipynb opens a
        # file that is not there to show students what the error looks like.
        # Those still have to run every cell; they are just allowed to have a
        # traceback among the outputs.
        self.allow_errors = allow_errors

    @property
    def abspath(self):
        return os.path.join(nbtools.REPO_ROOT, self.path)

    @property
    def executable(self):
        return self.status in ("run", "network")

    def __repr__(self):
        return "Entry({!r}, {!r})".format(self.path, self.status)


class Manifest(object):
    def __init__(self, entries, cell_timeout=600):
        self.entries = entries
        self.cell_timeout = cell_timeout

    def by_status(self, *statuses):
        return [e for e in self.entries if e.status in statuses]

    def get(self, path):
        for entry in self.entries:
            if entry.path == path:
                return entry
        return None

    @property
    def paths(self):
        return {e.path for e in self.entries}


def load_manifest(path=MANIFEST_PATH):
    data = _load_toml(path)
    options = data.get("options", {})
    allow_errors = set(options.get("allow_errors", []))

    entries = []
    for status in STATUSES:
        section = data.get(status, {})
        listed = section.get("notebooks", [])
        reasons = section.get("reasons", {})
        for name in listed:
            entries.append(Entry(name, status, reasons.get(name, ""),
                                 allow_errors=name in allow_errors))

    seen = {}
    for entry in entries:
        if entry.path in seen:
            raise SystemExit(
                "{} is listed twice in the manifest ({} and {})"
                .format(entry.path, seen[entry.path], entry.status)
            )
        seen[entry.path] = entry.status

    unknown = allow_errors - set(seen)
    if unknown:
        raise SystemExit(
            "options.allow_errors names notebooks that are not in the "
            "manifest: {}".format(", ".join(sorted(unknown)))
        )

    return Manifest(entries, cell_timeout=options.get("cell_timeout", 600))


if __name__ == "__main__":
    manifest = load_manifest()
    for status in STATUSES:
        rows = manifest.by_status(status)
        print("{} ({}):".format(status, len(rows)))
        for entry in rows:
            suffix = "  -- {}".format(entry.reason) if entry.reason else ""
            print("    {}{}".format(entry.path, suffix))
    sys.exit(0)
