# Synthetic threshold calibration

Evaluated 24 paired C3D/USD cases, including 4 clean negative controls.
All injected event labels are exact by construction. The baseline is analytic motion, so these results do not estimate real-world precision or recall.
Point events match within ±1 frame; interval events require IoU ≥ 0.5, with exact type and target names.
The cutoff operates on heuristic scores; it is not a probability threshold.

| Cutoff | TP | FP | FN | Precision | Recall | F1 | FP/min | Clean-control FP | Dev P/R | Held-out P/R |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 0.70 | 20 | 0 | 0 | 1.000 | 1.000 | 1.000 | 0.00 | 0 | 1.000/1.000 | 1.000/1.000 |
| 0.75 | 18 | 0 | 2 | 1.000 | 0.900 | 0.947 | 0.00 | 0 | 1.000/0.900 | 1.000/0.900 |
| 0.80 | 18 | 0 | 2 | 1.000 | 0.900 | 0.947 | 0.00 | 0 | 1.000/0.900 | 1.000/0.900 |
| 0.85 | 18 | 0 | 2 | 1.000 | 0.900 | 0.947 | 0.00 | 0 | 1.000/0.900 | 1.000/0.900 |
| 0.86 | 18 | 0 | 2 | 1.000 | 0.900 | 0.947 | 0.00 | 0 | 1.000/0.900 | 1.000/0.900 |
| 0.88 | 16 | 0 | 4 | 1.000 | 0.800 | 0.889 | 0.00 | 0 | 1.000/0.800 | 1.000/0.800 |
| 0.90 | 12 | 0 | 8 | 1.000 | 0.600 | 0.750 | 0.00 | 0 | 1.000/0.600 | 1.000/0.600 |
| 0.93 | 12 | 0 | 8 | 1.000 | 0.600 | 0.750 | 0.00 | 0 | 1.000/0.600 | 1.000/0.600 |
| 0.95 | 10 | 0 | 10 | 1.000 | 0.500 | 0.667 | 0.00 | 0 | 1.000/0.500 | 1.000/0.500 |
| 0.97 | 6 | 0 | 14 | 1.000 | 0.300 | 0.462 | 0.00 | 0 | 1.000/0.300 | 1.000/0.300 |
| 0.98 | 4 | 0 | 16 | 1.000 | 0.200 | 0.333 | 0.00 | 0 | 1.000/0.200 | 1.000/0.200 |
| 0.99 | 2 | 0 | 18 | 1.000 | 0.100 | 0.182 | 0.00 | 0 | 1.000/0.100 | 1.000/0.100 |
| 1.00 | 2 | 0 | 18 | 1.000 | 0.100 | 0.182 | 0.00 | 0 | 1.000/0.100 | 1.000/0.100 |

## Interpretation limits

- Development and held-out cases use different analytic motion variants, but both share a simple generated marker layout.
- Threshold selection should use the development split; the held-out split is for a one-time check.
- Synthetic negatives are useful regression controls but cannot stand in for expert-reviewed natural motion.
- Choose an operational false-alarm budget with mocap artists before claiming a production threshold.
- Candidate details and whether each candidate overlaps an injected event are in `candidate_events.csv`.
