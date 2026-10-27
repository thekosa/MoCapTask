# mocap-qc

A read-only command-line quality checker for C3D markers and a related UsdSkel animation.
It finds candidate defects, aligns both representations, and reports every event on the C3D timeline.
It never repairs, smooths, or exports changes to the input files.

## Setup and run

Tested on Windows with **64-bit Python 3.10.11**. Runtime dependencies are pinned in
`requirements.txt`; no GPU, licensed cleanup package, or network service is needed at runtime.

From this repository's root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mocap_qc mocap/data/take.c3d mocap/data/take.usd -o out
```

On Linux/macOS use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.
Only Windows was exercised for this submission. For runtime only, install
`requirements.txt` instead of `requirements-dev.txt`.

Optional installation as a command:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\mocap-qc.exe mocap/data/take.c3d mocap/data/take.usd -o out
```

## Outputs and options

- [out/report.md](out/report.md): artist-facing intervals, evidence, and conditional review suggestions.
- [out/report.json](out/report.json): **exactly** the schema requested in [the brief](mocap/BRIEF.md).
- [NOTES.md](NOTES.md): data conventions, detector rules, validation, and limitations.

The supplied take produces **12 events** at the default confidence cutoff of **0.80**,
and an estimated USD-to-C3D offset of **+18 frames**.
These are findings to review, not an independently verified count of all defects.

All event bounds are **inclusive, zero-based C3D frame indices**.
The offset is the C3D frame corresponding to the **first sampled USD pose**.
Marker labels retain their `A1:` namespace; joints retain their full hierarchical tokens.

The conservative default remains **0.80**. Use `--review-low-confidence` to select
**0.70** when you explicitly want a larger review queue. On the supplied take this
produces **25 events**, with the same **+18-frame** offset. The 13 additional events
are uncorroborated `marker_discontinuity` candidates: their truth is unknown, and they
require independent review before classifying them as defects or false alarms.

`--min-confidence 0.90` still selects a custom inclusive reporting threshold.
`--review-low-confidence` is equivalent to `--min-confidence 0.70`; combining those
two options is an argument error. Both settings filter the same detector output:
physical thresholds and heuristic score assignments are unchanged.
The score is a documented heuristic, **not a probability**.

The [synthetic pilot](calibration/README.md) contains 20 known injected events and
4 clean controls across two analytic motion variants. At 0.70 it detects 20/20
injected events; at 0.80 it detects 18/20. Both operating points produce zero alarms
on the four clean controls. These small synthetic results do **not** establish
precision or recall on real captures.

To request the review queue without replacing the default report:

```powershell
.\.venv\Scripts\python.exe -m mocap_qc mocap/data/take.c3d mocap/data/take.usd -o out-review --review-low-confidence
```

To reproduce the pilot, run
`.\.venv\Scripts\python.exe calibration/evaluate.py`; it regenerates the sweep
artifacts in `calibration/`. The separate `calibration/original-at-0.70/` report
is preserved as the supplied-take comparison.

`--max-offset-frames 240` expands the automatic timing search (default: +/-120 C3D frames).
For static/ambiguous motion or unknown pelvis labels, automatic timing fails explicitly.
Use `--offset-frames 18` only when that value has been independently established;
this bypasses the estimator and is marked as user-supplied in the human report.

Exit code 0 means reports were written; 2 means invalid arguments, input, or failed analysis.
An existing report is replaced on a successful run. A failed analysis does not refresh it:
check the exit status before relying on files from a previous run.

## Tests and code

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check mocap_qc tests tools
.\.venv\Scripts\python.exe -m ruff format --check mocap_qc tests tools
```

Tests inject known defects into controlled trajectories, include clean counterexamples,
read real generated C3D/USD fixtures, and exercise the CLI against the supplied take.
The integration test checks input SHA-256 hashes before and after analysis.

The processing path is deliberately small:

1. `readers.py` loads units, missing samples, animation mapping, and world/local poses.
2. `alignment.py` estimates the constant time offset using pelvis/root motion.
3. `marker_detectors.py` and `skeleton_detectors.py` find native-sample events.
4. `numerics.py` maps skeleton bounds onto C3D frames; `cross_checks.py` adds aligned context.
5. `pipeline.py` applies the reporting cutoff; `reporting.py` writes JSON and Markdown.
6. `cli.py` validates arguments and runs that pipeline.

On Windows, some native readers do not accept non-ASCII paths. The reader uses the
existing Windows short-path alias where available, without copying or editing inputs.
If short names are disabled and the native library cannot open the file, place the
whole project under an ASCII-only path.

## Submission archive

After committing all deliverables:

```powershell
.\.venv\Scripts\python.exe tools/package_submission.py
```

This creates `submission.zip`, containing tracked project files and **the complete
local .git directory** under `mocap-qc/`. It refuses a dirty worktree and verifies every
archived tracked file. The virtual environment, caches, scratch analysis, and the ZIP
itself are excluded. The recipient installs dependencies using the commands above.
