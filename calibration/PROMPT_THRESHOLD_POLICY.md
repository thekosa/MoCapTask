# Prompt: implement an evidence-based confidence cutoff policy

You are working in the `ZadanieRekrStudio` repository. Revise the tool's confidence-cutoff policy using the prepared calibration corpus and research summarized below. Make a concrete code change; do not only write recommendations.

## Evidence to use

Read `calibration/README.md`, `calibration/manifest.json`, `calibration/results.md`, and `calibration/original-at-0.70/report.md`.

- The corpus contains 24 paired synthetic cases: 20 known injected defects and 4 clean controls, split between two distinct analytic motion variants.
- At cutoff `0.70`, the detector finds 20/20 injected defects and produces 0 events on the 4 clean controls.
- At cutoff `0.80`, it finds 18/20 and produces 0 events on those controls. The two additional true positives at `0.70` are low-score marker discontinuities.
- On the supplied take, `0.80` produces 12 events. `0.70` produces 25; the 13 added events are all uncorroborated `marker_discontinuity` candidates. There are no truth labels for them, so they are unresolved—not known false alarms and not confirmed defects.
- `confidence` is a heuristic evidence score, not a probability. The small synthetic corpus cannot establish deployed precision or artist workload.
- The closest published study used manually cleaned motion, logged synthetic corruption, and a separate human-operator comparison. In one raw real-life recording, its detector proposed 29 events, an expert accepted 16 and rejected 13, and 4 were missed. This demonstrates why synthetic tests need expert-reviewed natural takes; these counts and the paper's detector settings are not thresholds to copy. Its test files are not publicly deposited. See Skurowski & Pawlyta (2022): https://www.mdpi.com/1424-8220/22/11/4076.

## Required implementation

1. Keep the current conservative default cutoff at `0.80`; the real take shows that globally defaulting to `0.70` would add 13 unresolved discontinuity alerts.
2. Add an explicit recall-oriented CLI switch, `--review-low-confidence`, that selects cutoff `0.70`. Keep `--min-confidence` as a numeric override, and reject using both options together with a clear error.
3. Ensure the human report states the active cutoff and continues to explain that scores are heuristic, not probabilities. Keep `report.json` in the exact schema from `mocap/BRIEF.md`.
4. Update README and NOTES to describe the two operating points and the measured synthetic trade-off. Do not claim the synthetic 100% precision/recall estimates real-world performance.
5. Do not alter detector-specific physical thresholds or score assignments in this task; this corpus only supports a reporting-cutoff policy change.
6. Add focused CLI tests for the new switch, the mutual-exclusion error, and unchanged numeric override behavior. Run the calibration evaluator and existing project checks. Confirm the original input data remain unchanged.

## Decision rule

Use `0.70` only when an artist explicitly wants a recall-oriented review queue and can adjudicate the extra marker-discontinuity candidates. Use `0.80` for the default report until natural takes have expert labels. Do not calibrate or describe either cutoff as a percentage probability.

## Expected deliverable

Commit-ready source and documentation changes, passing focused tests, with the calibration results and unresolved limitations recorded. Regenerate `out/` using the unchanged default `0.80`; keep the separate `calibration/original-at-0.70/` report as the comparison artifact.
