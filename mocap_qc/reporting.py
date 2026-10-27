"""A small artist-facing report and the exact JSON contract from the brief."""
import json
import os
from pathlib import Path
import tempfile

SUGGESTIONS = {
    "gap": "Inspect the missing marker interval; if confirmed, review gap filling against nearby valid markers.",
    "frozen_marker": "Check for held/interpolated coordinates; review the marker track before reconstructing this interval.",
    "label_swap": "Inspect both trajectories at the entry and return boundaries; if confirmed, correct their labels in the cleanup tool.",
    "spike": "Inspect the short excursion against neighboring samples and the original capture before replacing samples.",
    "marker_discontinuity": "Inspect both sides of this boundary for tracking/reconstruction changes; determine which side is trustworthy before editing.",
    "skeleton_translation_spike": "Inspect the root translation keys and the marker solve at this frame.",
    "rotation_excursion": "Inspect local joint rotation and its return boundary; review the solve/rotation keys against the marker motion.",
    "rotation_jump": "Inspect adjacent local rotation keys and verify whether the movement is intentional.",
    "bone_length_change": "Check local translation/scale keys and whether the rig intentionally changes bone length.",
    "invalid_joint": "Inspect the joint data and re-export or re-solve the affected interval if invalid.",
}


def markdown(analysis):
    m, s, a = analysis.markers, analysis.skeleton, analysis.alignment
    lines = [
        "# Motion-capture quality report", "",
        f"**{len(analysis.events)} reported events.** Inputs: `{m.metadata.get('file', 'C3D')}` and `{s.metadata.get('file', 'USD')}`.",
        f"C3D: {m.frames} frames at {m.rate:g} Hz; {len(m.names)} markers. "
        f"USD: {len(s.times)} poses at {s.rate:g} Hz; {len(s.names)} joints.", "",
        f"**Reporting threshold: confidence >= {analysis.min_confidence*100:.12g}%.** "
        f"Only candidates meeting this threshold are listed "
        f"({analysis.candidate_count - len(analysis.events)} lower-score candidates omitted). "
        "Confidence is a heuristic evidence score, **not a calibrated probability of error**. "
        "No listed event is an automatic instruction to repair the take.", "",
        f"**Time alignment: {a.offset:+d} C3D frames ({a.offset/m.rate:+.3f} s).** "
        f"The first sampled USD pose corresponds to C3D frame {a.offset}. "
        f"Method: {a.method}.",
    ]
    if "half_window_offsets" in a.details:
        halves = a.details["half_window_offsets"]
        lines.append(f"Separate first/second-half estimates: {halves[0]:+d} / {halves[1]:+d} frames.")
    lines += [
        "Every interval below uses **inclusive, zero-based C3D frame indices**, including skeleton events. "
        "Times are seconds from C3D sample 0; the end time is the timestamp of the last included sample.",
        "Skeleton intervals are mapped to the nearest C3D sample and clipped to the C3D recording. "
        "Cross-file evidence is limited to their overlapping time range.",
        "The skeleton was solved from the markers: agreement is useful context, not independent ground truth. "
        "**Input files have not been modified.**", "",
    ]
    if not all(s.metadata.get(k, True) for k in ("units_authored", "axis_authored")):
        lines += ["**Metadata caution:** USD units or up axis were not authored; OpenUSD defaults were used.", ""]
    if not analysis.events:
        lines += ["No events passed the configured threshold. This does not certify that the take is free of defects.", ""]
    for i, event in enumerate(analysis.events, 1):
        targets = ", ".join(f"`{name}`" for name in event.targets)
        lines += [
            f"## {i}. {event.type.replace('_', ' ')} â€” frames {event.start}â€“{event.end}", "",
            f"**Targets:** {targets}  ",
            f"**Time:** {event.start/m.rate:.3f}â€“{event.end/m.rate:.3f} s | **Confidence:** {event.confidence:.0%}", "",
            event.note, "",
            "**Suggested review:** " + SUGGESTIONS.get(event.type, "Review the indicated interval in the capture/animation viewer."),
            "",
        ]
    lines += [
        "---", "",
        "Detection rules, tested cases, and known limitations are documented in `NOTES.md` at the repository root. "
        "The JSON report carries the same events; this report adds review suggestions only.",
        "",
    ]
    return "\n".join(lines)


def validate_output(output_dir, input_paths):
    output_dir = Path(output_dir).resolve()
    inputs = {Path(p).resolve() for p in input_paths}
    for name in ("report.json", "report.md"):
        target = output_dir / name
        if target.resolve() in inputs:
            raise ValueError(f"Output {name} would overwrite an input file.")
        if target.is_symlink():
            raise ValueError(f"Refusing to replace symbolic-link output: {target}")
    return output_dir


def write_reports(analysis, output_dir, input_paths=()):
    output_dir = validate_output(output_dir, input_paths)
    contents = {
        "report.json": json.dumps(analysis.as_dict(), indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        "report.md": markdown(analysis),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = []
    try:
        # Complete both serializations before touching either previous report.
        for name, content in contents.items():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=output_dir, prefix=".qc-", suffix=".tmp", delete=False) as stream:
                path = Path(stream.name)
                temporary.append((path, output_dir / name))
                stream.write(content)
        for path, target in temporary:
            os.replace(path, target)
    finally:
        for path, _ in temporary:
            path.unlink(missing_ok=True)
