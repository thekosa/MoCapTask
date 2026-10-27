"""Sweep confidence cutoffs against the exact labels in manifest.json."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mocap_qc.pipeline import analyze  # noqa: E402


THRESHOLDS = (0.70, 0.75, 0.80, 0.85, 0.86, 0.88, 0.90, 0.93, 0.95, 0.97, 0.98, 0.99, 1.00)


def same_event(predicted: dict, expected: dict, manifest: dict) -> bool:
    if predicted["type"] != expected["type"] or predicted["targets"] != expected["targets"]:
        return False
    p0, p1 = predicted["start"], predicted["end"]
    g0, g1 = expected["start"], expected["end"]
    if g0 == g1:
        tolerance = manifest["matching_policy"]["point_event_tolerance_frames"]
        return abs(p0 - g0) <= tolerance and abs(p1 - g1) <= tolerance
    intersection = max(0, min(p1, g1) - max(p0, g0) + 1)
    union = max(p1, g1) - min(p0, g0) + 1
    return intersection / union >= manifest["matching_policy"]["interval_event_iou_minimum"]


def count_matches(cases: list[dict], threshold: float, manifest: dict) -> dict:
    tp = fp = fn = 0
    negative_fp = 0
    all_predicted = 0
    event_types: dict[str, dict[str, int]] = {}
    for case in cases:
        predicted = [e for e in case["candidates"] if e["confidence"] >= threshold]
        expected = case["known_events"]
        all_predicted += len(predicted)
        used_predictions: set[int] = set()
        used_expected: set[int] = set()
        pairs = []
        for pi, event in enumerate(predicted):
            for gi, gold in enumerate(expected):
                if same_event(event, gold, manifest):
                    pairs.append((pi, gi))
        for pi, gi in pairs:
            if pi not in used_predictions and gi not in used_expected:
                used_predictions.add(pi)
                used_expected.add(gi)
        tp += len(used_expected)
        case_fp = len(predicted) - len(used_predictions)
        fp += case_fp
        fn += len(expected) - len(used_expected)
        if not expected:
            negative_fp += case_fp
        for gold in expected:
            label = gold["type"]
            bucket = event_types.setdefault(label, {"tp": 0, "fn": 0})
            if any(same_event(predicted[pi], gold, manifest) for pi in used_predictions):
                bucket["tp"] += 1
            else:
                bucket["fn"] += 1

    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else 0.0
    total_minutes = sum(c["frames"] / c["rate_hz"] / 60 for c in cases)
    for label, values in event_types.items():
        values["precision"] = None
        values["recall"] = values["tp"] / (values["tp"] + values["fn"]) if values["tp"] + values["fn"] else None
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_alarms_per_minute": fp / total_minutes if total_minutes else 0.0,
        "negative_control_false_alarms": negative_fp,
        "reported_events": all_predicted,
        "event_type_recall": event_types,
    }


def fmt(value):
    return "n/a" if value is None else f"{value:.3f}"


def main() -> None:
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    cases = []
    for item in manifest["cases"]:
        c3d = HERE / item["c3d"]
        usd = HERE / item["usd"]
        analysis = analyze(c3d, usd, min_confidence=0.0, offset_frames=item["offset_frames"])
        cases.append(
            {
                **item,
                "candidates": [event.as_dict() for event in analysis.events],
            }
        )

    rows = []
    for threshold in THRESHOLDS:
        row = count_matches(cases, threshold, manifest)
        row["development"] = count_matches(
            [case for case in cases if case["split"] == "development"], threshold, manifest
        )
        row["heldout"] = count_matches(
            [case for case in cases if case["split"] == "heldout"], threshold, manifest
        )
        rows.append(row)

    candidate_rows = []
    for case in cases:
        for event in case["candidates"]:
            candidate_rows.append(
                {
                    "case_id": case["case_id"],
                    "split": case["split"],
                    "type": event["type"],
                    "targets": ",".join(event["targets"]),
                    "start": event["start"],
                    "end": event["end"],
                    "confidence": event["confidence"],
                    "known_injected_event": any(
                        same_event(event, gold, manifest) for gold in case["known_events"]
                    ),
                }
            )

    with (HERE / "candidate_events.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("case_id", "split", "type", "targets", "start", "end", "confidence", "known_injected_event"),
        )
        writer.writeheader()
        writer.writerows(candidate_rows)

    result = {
        "description": "Threshold sweep against synthetic injected-event labels; not a real-world accuracy estimate.",
        "thresholds_are_heuristic_cutoffs_not_probabilities": True,
        "event_matching": manifest["matching_policy"],
        "case_count": len(cases),
        "negative_control_count": sum(not c["known_events"] for c in cases),
        "results": rows,
        "candidates": candidate_rows,
    }
    (HERE / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Synthetic threshold calibration",
        "",
        f"Evaluated {len(cases)} paired C3D/USD cases, including {result['negative_control_count']} clean negative controls.",
        "All injected event labels are exact by construction. The baseline is analytic motion, so these results do not estimate real-world precision or recall.",
        "Point events match within ±1 frame; interval events require IoU ≥ 0.5, with exact type and target names.",
        "The cutoff operates on heuristic scores; it is not a probability threshold.",
        "",
        "| Cutoff | TP | FP | FN | Precision | Recall | F1 | FP/min | Clean-control FP | Dev P/R | Held-out P/R |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in rows:
        dev = row["development"]
        hold = row["heldout"]
        lines.append(
            f"| {row['threshold']:.2f} | {row['tp']} | {row['fp']} | {row['fn']} | "
            f"{fmt(row['precision'])} | {fmt(row['recall'])} | {row['f1']:.3f} | "
            f"{row['false_alarms_per_minute']:.2f} | {row['negative_control_false_alarms']} | "
            f"{fmt(dev['precision'])}/{fmt(dev['recall'])} | "
            f"{fmt(hold['precision'])}/{fmt(hold['recall'])} |"
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- Development and held-out cases use different analytic motion variants, but both share a simple generated marker layout.",
        "- Threshold selection should use the development split; the held-out split is for a one-time check.",
        "- Synthetic negatives are useful regression controls but cannot stand in for expert-reviewed natural motion.",
        "- Choose an operational false-alarm budget with mocap artists before claiming a production threshold.",
        "- Candidate details and whether each candidate overlaps an injected event are in `candidate_events.csv`.",
        "",
    ]
    (HERE / "results.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Evaluated {len(cases)} cases at {len(THRESHOLDS)} cutoffs. Wrote calibration/results.md and results.json.")


if __name__ == "__main__":
    main()
