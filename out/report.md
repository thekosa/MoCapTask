# Motion-capture quality report

**12 reported events.** Inputs: `take.c3d` and `take.usd`.
C3D: 3600 frames at 120 Hz; 82 markers. USD: 3600 poses at 120 Hz; 60 joints.

**Reporting threshold: confidence >= 80%.** Only candidates meeting this threshold are listed (13 lower-score candidates omitted). Confidence is a heuristic evidence score, **not a calibrated probability of error**. No listed event is an automatic instruction to repair the take.

**Time alignment: +18 C3D frames (+0.150 s).** The first sampled USD pose corresponds to C3D frame 18. Method: Robust pelvis/root velocity alignment.
Separate first/second-half estimates: +18 / +18 frames.
Every interval below uses **inclusive, zero-based C3D frame indices**, including skeleton events. Times are seconds from C3D sample 0; the end time is the timestamp of the last included sample.
Skeleton intervals are mapped to the nearest C3D sample and clipped to the C3D recording. Cross-file evidence is limited to their overlapping time range.
The skeleton was solved from the markers: agreement is useful context, not independent ground truth. **Input files have not been modified.**

## 1. spike — frames 300–301

**Targets:** `A1:LFHD`  
**Time:** 2.500–2.508 s | **Confidence:** 95%

Short excursion 45.0 mm from the local bridge; opposing entry/exit jumps and quiet surrounding samples (minimum amplitude 15.0 mm). Aligned Head joint-origin bridge deviation: 0.4 mm.

**Suggested review:** Inspect the short excursion against neighboring samples and the original capture before replacing samples.

## 2. frozen marker — frames 1000–1060

**Targets:** `A1:LELB`  
**Time:** 8.333–8.833 s | **Confidence:** 98%

XYZ repeats to 1 nm for 61 samples while nearby markers move a median 468.8 mm between the endpoints, with a discontinuous entry/release. Possible held samples.

**Suggested review:** Check for held/interpolated coordinates; review the marker track before reconstructing this interval.

## 3. rotation excursion — frames 1200–1215

**Targets:** `Hips/Spine/Spine1/Spine2/Spine3/RightShoulder/RightArm/RightForeArm`  
**Time:** 10.000–10.125 s | **Confidence:** 97%

Joint-local orientation changes by up to 180.0 degrees between samples (threshold 35.0); quaternion sign changes are ignored. Across the aligned interval, the two wrist markers change their connecting-axis direction by at most 0.4 degrees per C3D frame.

**Suggested review:** Inspect local joint rotation and its return boundary; review the solve/rotation keys against the marker motion.

## 4. spike — frames 1377–1377

**Targets:** `A1:RIWR`  
**Time:** 11.475–11.475 s | **Confidence:** 90%

Short excursion 24.7 mm from the local bridge; opposing entry/exit jumps and quiet surrounding samples (minimum amplitude 15.0 mm). Aligned RightHand joint-origin bridge deviation: 0.2 mm.

**Suggested review:** Inspect the short excursion against neighboring samples and the original capture before replacing samples.

## 5. spike — frames 1450–1450

**Targets:** `A1:RKNE`  
**Time:** 12.083–12.083 s | **Confidence:** 95%

Short excursion 30.2 mm from the local bridge; opposing entry/exit jumps and quiet surrounding samples (minimum amplitude 15.0 mm). Aligned RightLeg joint-origin bridge deviation: 0.3 mm.

**Suggested review:** Inspect the short excursion against neighboring samples and the original capture before replacing samples.

## 6. marker discontinuity — frames 1707–1707

**Targets:** `A1:RRNG6`  
**Time:** 14.225–14.225 s | **Confidence:** 86%

Estimated position step 46.6 mm between locally smooth tracks (fit RMS 0.45 mm; 0 stable-distance references corroborate it). The cause and which side is correct require review.

**Suggested review:** Inspect both sides of this boundary for tracking/reconstruction changes; determine which side is trustworthy before editing.

## 7. marker discontinuity — frames 1778–1778

**Targets:** `A1:CLAV`  
**Time:** 14.817–14.817 s | **Confidence:** 86%

Estimated position step 115.2 mm between locally smooth tracks (fit RMS 0.37 mm; 0 stable-distance references corroborate it). The cause and which side is correct require review.

**Suggested review:** Inspect both sides of this boundary for tracking/reconstruction changes; determine which side is trustworthy before editing.

## 8. skeleton translation spike — frames 2000–2000

**Targets:** `Hips`  
**Time:** 16.667–16.667 s | **Confidence:** 96%

Short excursion 60.1 mm from the local bridge; opposing entry/exit jumps and quiet surrounding samples (minimum amplitude 15.0 mm). Aligned pelvis-marker centroid bridge deviation: 0.1 mm. This supports a skeleton-only excursion.

**Suggested review:** Inspect the root translation keys and the marker solve at this frame.

## 9. label swap — frames 2200–2260

**Targets:** `A1:LIWR`, `A1:LOWR`  
**Time:** 18.333–18.833 s | **Confidence:** 97%

At both interval boundaries, exchanging these two marker labels reduces the linear continuation error by at least 80%; the labels return afterward.

**Suggested review:** Inspect both trajectories at the entry and return boundaries; if confirmed, correct their labels in the cleanup tool.

## 10. gap — frames 2600–2660

**Targets:** `A1:RTOE`  
**Time:** 21.667–22.167 s | **Confidence:** 100%

61 invalid samples (0.508 s): negative/non-finite residual or non-finite XYZ.

**Suggested review:** Inspect the missing marker interval; if confirmed, review gap filling against nearby valid markers.

## 11. marker discontinuity — frames 2665–2665

**Targets:** `A1:T145_cluster_LCM_5`  
**Time:** 22.208–22.208 s | **Confidence:** 88%

Estimated position step 18.4 mm between locally smooth tracks (fit RMS 1.43 mm; 3 stable-distance references corroborate it). The cause and which side is correct require review.

**Suggested review:** Inspect both sides of this boundary for tracking/reconstruction changes; determine which side is trustworthy before editing.

## 12. marker discontinuity — frames 3000–3000

**Targets:** `A1:RTHI`  
**Time:** 25.000–25.000 s | **Confidence:** 86%

Estimated position step 20.1 mm between locally smooth tracks (fit RMS 0.19 mm; 0 stable-distance references corroborate it). The cause and which side is correct require review.

**Suggested review:** Inspect both sides of this boundary for tracking/reconstruction changes; determine which side is trustworthy before editing.

---

Detection rules, tested cases, and known limitations are documented in `NOTES.md` at the repository root. The JSON report carries the same events; this report adds review suggestions only.
