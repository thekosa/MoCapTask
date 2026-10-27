# Threshold calibration fixtures

This folder contains a reproducible pilot corpus for choosing the report cutoff.
It does not alter the supplied take or the detector implementation.

## Contents

- `generate.py` creates 24 paired C3D/USD cases (48 input files): 20 injected defects and 4 clean controls.
- `data/development/` and `data/heldout/` contain two different smooth motion variants. Each split has 10 labeled fault cases and 2 negative controls.
- `manifest.json` records the exact injected defect type, target, and inclusive sample interval. USD and C3D frame 0 are deliberately aligned, so calibration uses the known `--offset-frames 0`.
- `evaluate.py` runs the existing detectors at confidence cutoffs from 0.70 through 1.00 and measures event-level TP/FP/FN. Point events allow ±1 frame; interval events require IoU ≥0.5 with the same type and targets.
- `results.md`, `results.json`, and `candidate_events.csv` contain the observed sweep.
- `original-at-0.70/` shows what the lower cutoff does to the supplied take.
- `PROMPT_THRESHOLD_POLICY.md` is a ready-to-use implementation prompt based on these results and the literature.

Regenerate the fixtures and rerun the sweep from the repository root:

```powershell
.\.venv\Scripts\python.exe calibration\generate.py
.\.venv\Scripts\python.exe calibration\evaluate.py
```

## Pilot result

At `0.70`, all 20 injected events are detected with no alarms among the 4 synthetic clean controls. At `0.80`, 18/20 are detected, also with no synthetic false alarms. The two extra detections at `0.70` are deliberately weak marker-step cases assigned heuristic score `0.70`. The development and held-out splits each show the same 10/10 versus 9/10 recall difference.

That result alone does **not** justify changing the default for real captures. On the supplied take, changing from `0.80` to `0.70` increases the report from 12 to 25 events. All 13 additional events are uncorroborated `marker_discontinuity` candidates; their truth is unknown. They must not be called false positives without expert review, but they demonstrate the artist-facing cost that the synthetic controls cannot measure.

Therefore the empirical evidence supports offering `0.70` as an explicit recall-oriented review setting, while retaining `0.80` as the conservative default until natural takes are labeled. Neither number is a probability. The pilot is small, analytic, and not a production calibration.

## Research context

Skurowski and Pawlyta tested mocap artifact detection with manually cleaned baseline motion, injected artifacts with logged locations/types, and a separate comparison against human operators. In one raw real-life recording, their detector proposed 29 events, an expert accepted 16 and rejected 13, and 4 were missed. This illustrates the precision/recall trade-off; those counts and their detector settings are not thresholds to copy. The paper does not provide a public labeled file bundle for reuse, and its data availability statement is “not applicable.” [Paper](https://www.mdpi.com/1424-8220/22/11/4076)

For broader future calibration, the [AddBiomechanics Core Dataset](https://addbiomechanics.org/download_data.html) offers a manually reviewed, publicly downloadable base collection of marker observations and kinematics. It is not an artifact-labeled benchmark, so injected labels and expert-reviewed natural defects would still be needed.
