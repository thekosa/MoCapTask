# Implementation notes

## Scope and data discoveries

This is a focused take-home implementation within the brief's four-hour timebox.
The tool reports defects; no input repair is implemented. Report review suggestions are advisory.

The C3D contains 3,600 samples at 120 Hz and 82 named markers, with positions in **mm**.
Names include the `A1:` prefix. Internal calculations use metres. C3D frame indices in
the report start at zero, irrespective of acquisition header numbering.
The point residual is zero for every valid sample; it therefore cannot rank measurement
quality here. The 61 invalid samples have negative residuals and NaN positions, all on
RTOE at frames 2600â€“2660. Zero XYZ coordinates and zero residuals are not gaps.

The USD is binary USDC with one skeleton, `/A1/Skeleton`, and 60 joints.
Its animation has 3,600 regular authored samples at timecodes 0â€“3599.
Both `timeCodesPerSecond` and `framesPerSecond` are 120, but the reader uses the former
for time conversion. USD units are **0.01 metres per unit**, with authored **Y up**.
C3D geometry is consistent with **Z up**; that is an inference, not an authored C3D axis declaration.

UsdSkel resolves the animation-to-skeleton joint mapping. Joint hierarchy and all
ancestor prim transforms are evaluated for each pose. World joint origins are used
for position/length tests; joint-local quaternions are used for angular tests.
The NumPy view of the USD quaternion array is **xyzw**. Quaternions q and -q represent
the same orientation and are deliberately treated identically.
The supplied local bone translations and scales are stable; no bone-length event passes the detector.

## Synchronization and comparison

Both files describe the same performer/take, but markers are skin/cluster points and
skeleton joints are solved anatomical/rig origins. Their positions are not interchangeable.

The estimator averages available waist markers, compares their velocities to root
velocity, and searches integer C3D offsets. A proper spatial rotation is fitted with
SVD at each offset, trimming the largest 10% of residuals over three iterations.
There is no fitted scale, reflection, time warp, or input mutation. Different sample
rates are supported by resampling the root for synchronization only.

The best offset is **+18 frames (0.150 s)**. Independent searches in the first and second
halves both choose +18. The fitted rotation is approximately USD `(x, y, z)` to C3D
`(x, -z, y)`; the trimmed velocity discrepancy is about **0.0507 m/s**.
The next best offset, +19, has about **14.5%** greater residual error.
The rotation is used for timing, not to claim a marker should coincide with a joint.

The default search is +/-120 frames. Static/insufficiently varying motion, a winner at
the search edge, a close runner-up, a poor fit, or inconsistent half-window estimates
cause an explicit error. A verified manual offset is available; zero is never guessed.

Detection runs at each stream's native sample rate. USD event bounds are converted
by `floor(relative_seconds * C3D_rate + 0.5) + offset`, then clipped to valid C3D indices.
The last 18 USD samples lie beyond the C3D coverage after alignment; events wholly
outside that range are omitted. Cross-file checks do not extrapolate.

Cross-file context compares short local deviations or wrist-axis changes, rather than
absolute marker-to-joint distances. A quiet corresponding joint/marker track can
slightly strengthen evidence. Shared motion never automatically cancels a candidate:
the skeleton is derived from these markers and their errors can be correlated.

## Detectors and controlled checks

Distances below are physical distances after unit conversion. Robust thresholds use
`max(physical_floor, median + k * 1.4826 * MAD)`; k defaults to 12, or 20 for rotations.

- **gap:** consecutive invalid C3D samples (negative/non-finite residual or non-finite XYZ).
  Tested with generated C3D files in mm, cm, and m, and an exact inclusive six-sample gap.
- **frozen_marker:** exactly repeated XYZ to 1 nm for at least max(6, 0.08 * rate) samples,
  moving nearby markers, and a discontinuous entry/release exceeding 15 mm and eight
  times the typical step. Tested with held coordinates and with planted markers and
  an entirely stationary take that must remain unflagged.
- **spike / skeleton_translation_spike:** 1â€“3 sample excursions exceeding a robust
  15 mm floor, opposing entry/exit jumps, a small jump residual, and quiet surrounding
  curvature. Root-only skeleton position checking avoids duplicate inherited alarms.
  Tested at each supported duration, with exact boundaries, noisy trajectories,
  and clean rapid smooth motion.
- **label_swap:** two simultaneous trajectory breaks become substantially more
  continuous when their labels are exchanged: error decreases by at least 80%.
  A corresponding return boundary is required. Tested with a known bounded swap
  and a natural crossing that must not count as a swap.
- **marker_discontinuity:** two 10-sample quadratic fits reveal a position step above
  18 mm and 12 times the fit RMS, with fit RMS below 2 mm. Nearby candidates merge
  into a single boundary. Higher scores require very clean fits or corroboration by
  changes in otherwise stable inter-marker distances. Tested with a known step.
  This reports the boundary only; it cannot determine which side is wrong.
- **rotation_jump / rotation_excursion:** shortest quaternion angle exceeds a robust
  35-degree-per-sample floor. Opposing jumps within 0.5 s, returning near the previous
  orientation, form one interval. Tested with a known 180-degree excursion, q/-q sign
  changes, and smooth rapid rotation.
- **bone_length_change:** world parent-to-joint length deviates from its robust baseline
  by more than the larger of 5 mm, 5% of median length, and the robust noise limit.
  A controlled local length change tests the exact interval. Intentional scale animation
  remains a possible false positive.
- **invalid_joint:** non-finite evaluated pose/rotation or a degenerate quaternion
  becomes a reported invalid interval.

Tests also cover known positive, negative, and zero timing offsets; 60/120 Hz sampling;
rotated/translated coordinate systems; corrupted root samples; ambiguous stationary
motion; reordered USD animation joints; parent transforms; inclusive bounds, clipping,
confidence filtering, JSON schema, deterministic serialization, and read-only CLI execution.
The final local suite passes **45 tests** on Windows/Python 3.10.11.
These controlled tests verify mechanisms and counterexamples, not population-wide accuracy.

## Confidence and supplied-take results

Confidence is a **heuristic evidence score**, not a calibrated probability, accuracy,
or percentage speed deviation. The inclusive default cutoff **0.80** is printed in the
human report. Lower-scoring candidates are counted but omitted from both event lists.

The score rules are explicit: gaps/invalid joints 1.00, frozen markers 0.98, paired swaps
0.97, rotation excursions 0.96, isolated rotation jumps 0.86, bone-length changes 0.88.
Short position spikes score 0.88, or 0.93 above twice their adaptive threshold.
A quiet aligned joint adds 0.02 (capped at 0.97); a quiet pelvis strengthens a root
spike to at least 0.96; a stable wrist axis strengthens a forearm excursion to 0.97.
Position steps score 0.70 by default, 0.86 when fit RMS <=0.5 mm and jump/RMS >=50,
or 0.88 with at least two stable-distance references changing by more than 3 mm.
Stable references have median distance 10â€“200 mm and scaled MAD below 0.8 mm.

At the default cutoff the report contains 12 events:
LFHD 300â€“301; LELB 1000â€“1060; RightForeArm 1200â€“1215; RIWR 1377; RKNE 1450;
RRNG6 1707; CLAV 1778; Hips 2000; LIWR/LOWR 2200â€“2260; RTOE 2600â€“2660;
T145_cluster_LCM_5 at 2665; RTHI 3000.

The four discontinuity findings were additionally inspected on local and wider XYZ
plots. They show sharp positional breaks; this does not establish their cause.
For example, the CLAV boundary does not justify labeling a whole preceding smooth
segment as corrupt. The complete event evidence is in the generated report.
There are no provided truth labels, so precision/recall on the supplied take is **unknown**.
No event frame numbers or these marker-specific findings are hardcoded in detection.

## Deliberate limits and next work

This prioritizes interpretable, conservative detection over recall. It may miss slow drift,
small spikes, longer excursions, noise bursts, smooth bad interpolation, unmatched
label swaps, or defects near file ends (local context windows are required).
The fixed sample windows and angular floors target the provided 120 Hz take;
although timing conversion supports different rates, detection sensitivity is not
guaranteed to be rate invariant. Multiple skeletons and irregular/sparse pose sampling
are not supported. Automatic timing assumes a constant integer-frame offset and known
pelvis naming; drift or a subframe offset requires an extension.

Genuine abrupt impacts or unusual articulation can resemble trajectory breaks.
Stable-distance support can be misleading for skin markers or a damaged reference.
A hold that releases smoothly may be missed; a legitimate abrupt release can be flagged.
Correlated marker/solve defects can escape cross-checking. Anatomy/ground-contact rules
were omitted because rig conventions and intended motion are not established.
The tool does not claim to locate every planted problem.

Next steps would be expert-labeled captures, rate-aware thresholds, precision/recall and
interval-overlap evaluation on held-out takes, calibrated scores, configurable marker maps,
and robust cluster residuals for gradual defects. A viewer overlay would help review;
it is not needed for the requested CLI/report deliverable. No licensed cleanup package
was installed and no external-program benchmark was performed.

## Sources and methodological influence

- [C3D residual convention](https://www.c3d.org/HTML/Documents/gloss_residual.htm):
  negative residuals indicate invalidity; zero denotes processed/estimated points.
- [OpenUSD UsdSkel documentation](https://openusd.org/dev/api/usd_skel_page_front.html):
  joint hierarchy, animation mapping, and evaluated transforms.
- [Skurowski & Pawlyta (2022), Detection and Classification of Artifact Distortions
  in Optical Motion Capture Sequences](https://pmc.ncbi.nlm.nih.gov/articles/PMC9185486/):
  motivates combining temporal derivatives, prediction, and marker context, and testing
  deliberately injected artifacts. This implementation is a smaller rule set, not a
  reproduction of their filtering, morphology, predictor, or reported performance.
- [Gloersen & Federolf (2016), Predicting Missing Marker Trajectories in Human Motion
  Data Using Marker Intercorrelations](https://pmc.ncbi.nlm.nih.gov/articles/PMC4816448/):
  supports considering inter-marker information and validating on controlled gaps.
  Their PCA reconstruction is **not implemented**; repair is outside this project's scope.
