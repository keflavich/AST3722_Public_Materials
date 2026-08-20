# AST3722_Public_Materials

## Two branches

| branch | notebooks | what it's for |
| --- | --- | --- |
| `master` | outputs stripped | where you edit. Diffs show changed code and prose instead of changed base64 PNGs. |
| `executed` | outputs included | generated. Read notebooks here (and on nbviewer) to see the plots without running anything. |

`executed` is rebuilt automatically every time `master` is pushed, by
[`.github/workflows/build-executed.yml`](.github/workflows/build-executed.yml) —
you only ever push `master`. Never commit to `executed`; the next build
overwrites it.

**After cloning, run this once:**

```bash
./tools/install_hooks.sh
```

That configures a git filter which strips notebook outputs as they are staged,
so you can run a notebook, look at the plots, and commit without thinking about
it — your working copy keeps its outputs, git records only the code. It also
installs a post-commit hook that says so loudly if outputs get into a commit
anyway (a filter that was never configured is a silent no-op in git, which is
exactly the failure this catches).

To strip outputs on disk as well:

```bash
python tools/strip_outputs.py            # all notebooks
python tools/strip_outputs.py --check    # just report which ones are dirty
```

## Tests

```bash
pip install -r requirements-test.txt
pytest                    # structure checks + the notebooks that run offline
pytest -m network         # also the ones that query SESAME/SIMBAD/VizieR/SkyView
```

[`notebooks.toml`](notebooks.toml) says what the suite does with each notebook:
executes it (`run`), executes it but tolerates an upstream outage (`network`),
or checks only that it is a valid notebook because it needs observing data that
isn't in this repository (`needs-data`) or has cells students are meant to fill
in (`exercise`). Every notebook must be listed, so adding one forces the
question of how it gets tested.

CI runs the executable notebooks on Python 3.11 through 3.15
([`.github/workflows/test-notebooks.yml`](.github/workflows/test-notebooks.yml)),
weekly as well as on every push, so a library release that breaks a lab shows up
before a student hits it.

Lecture materials and demos (intended to be shown as RISE presentations):
 * [CCDs overview](<CCDs Overview - Data Reduction.ipynb>) [RISE](https://nbviewer.org/format/slides/github/keflavich/AST3722_Public_Materials/blob/executed/CCDs%20Overview%20-%20Data%20Reduction.ipynb#) - What's in a CCD image?  Bias, sky, dark.  A brief visual lecture
 * [Data Reduction Walkthrough](DataReductionWalkthrough.ipynb) [RISE](https://nbviewer.org/format/slides/github/keflavich/AST3722_Public_Materials/blob/executed/DataReductionWalkthrough.ipynb#)
 * [Directory Structure (basic UNIX intro)](DirectoryStructure.ipynb) [RISE](https://nbviewer.org/format/slides/github/keflavich/AST3722_Public_Materials/blob/executed/DirectoryStructure.ipynb#)
 * [Machine Readable Tables](MachineReadableTables.ipynb) [RISE](https://nbviewer.org/format/slides/github/keflavich/AST3722_Public_Materials/blob/executed/MachineReadableTables.ipynb#)
 * [Planet Observation Planning](<Planet Observation Planning.ipynb>) [RISE](https://nbviewer.org/format/slides/github/keflavich/AST3722_Public_Materials/blob/executed/Planet%20Observation%20Planning.ipynb#)
 * [Shifting Images: Demo with Jupiter](Shifting.ipynb) [RISE](https://nbviewer.org/format/slides/github/keflavich/AST3722_Public_Materials/blob/executed/Shifting.ipynb#)


Exercises:
* [Detector Characterization (CMOS)](<Detector Characterization (CMOS) - Bias, Darks, Gain, Flats.ipynb>) - bias, darks, gain, and flats for the ZWO ASI294mm cameras now in use at CTO
* [CCD Reduction Part 2: count statistics](<CCDs - Count Statistics - Exercise.ipynb>) - noise calculation, gain.
* [CCD Reduction Part 2: count statistics](<CCDs - Photon Count Statistics.ipynb>) - filled in version of [CCD Reduction Part 2: count statistics](CCDs - Count Statistics - Exercise.ipynb)
* [Data Reduction of a Single CCD frame: Exercise](DataReduction_SingleFrame_exercise_filled.ipynb)
* [Data Reduction of a Single CCD frame: Answer Key](DataReduction_SingleFrame_exercise.ipynb)
* [Long vs. Short Exposures - Exercise](<Long Exposures or Short Exposures.ipynb>)
* [Long vs. Short Exposures - Answer Key](LongOrShortAnswerKey.ipynb)
* [Observation Planning Exercise: Part 1](<Observation Planning Exercise.ipynb>)
* [Observation Planning Exercise: Part 1 (answer key)](<Observation Planning.ipynb>)
* [Observation Planning Exercise: Part 2](<Observation Planning Part 2 Exercise.ipynb>)
* [Observation Planning Exercise: Part 2 (answer key)](<Observation Planning Part 2.ipynb>)
* [Observation Planning Exercise: Part 3](<Observation Planning Part 3 Exercise.ipynb>)
* [Observation Planning Exercise: Part 3 (answer key)](<Observation Planning Part 3.ipynb>)
* [Observation Planning Exercise: Space-based](<Observation Planning - Space-based - Exercise.ipynb>)
* [Observation Planning Exercise: Space-based (answer key)](<Observation Planning - Space-Based.ipynb>)
* [Signal-to-Noise Ratio (answer key)](<SNR Investigation Continued (answer key 1).ipynb>)
* [Signal-to-Noise Ratio (answer key)](<SNR Investigation Continued (answer key two).ipynb>)
* [Signal-to-Noise Ratio exercise](<SNR Investigation Continued.ipynb>)

Other stuff:
 * [debug notebook](debug_notebook.ipynb)
 * [Alt/Az calculations](AltAzcalculations.ipynb)
 * [Obsolete/old version of CCD data reduction](CCDReductionLabExercise.ipynb)
 * [Detector Characterization (CCD)](<Detector Characterization (CCD) - Bias and Darks.ipynb>) - the CCD-era version, superseded by the CMOS one above; still the only notebook covering dark subtraction on an on-sky image
 * [Fitting - simplified](<Fitting - Simple Version.ipynb>) - incomplete notebook
