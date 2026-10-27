"""Run detectors in their native sampling, then publish on the C3D timeline."""

from dataclasses import dataclass
import math

from .alignment import estimate_alignment
from .cross_checks import add_context
from .marker_detectors import detect_markers
from .models import Alignment, Event, MarkerTake, SkeletonTake
from .numerics import map_skeleton_event
from .readers import read_c3d, read_usd
from .skeleton_detectors import detect_skeleton


@dataclass
class Analysis:
    markers: MarkerTake
    skeleton: SkeletonTake
    alignment: Alignment
    events: list[Event]
    min_confidence: float
    candidate_count: int

    def as_dict(self):
        # The brief requires exactly this schema. Extra metadata belongs in Markdown.
        return {
            "skel_to_c3d_offset_frames": int(self.alignment.offset),
            "events": [event.as_dict() for event in self.events],
        }


def analyze(
    c3d_path,
    usd_path,
    *,
    min_confidence=0.80,
    offset_frames=None,
    max_offset_frames=120,
):
    if not math.isfinite(min_confidence) or not 0 <= min_confidence <= 1:
        raise ValueError("--min-confidence must be a finite number between 0 and 1.")
    markers = read_c3d(c3d_path)
    skeleton = read_usd(usd_path)
    if offset_frames is None:
        alignment = estimate_alignment(markers, skeleton, max_offset_frames)
    else:
        # An explicit value is useful for captures with unknown marker conventions.
        if (
            offset_frames >= markers.frames
            or skeleton.times[-1] * markers.rate + offset_frames < 0
        ):
            raise ValueError(
                "--offset-frames leaves no overlap with the C3D recording."
            )
        alignment = Alignment(
            int(offset_frames), "User-supplied offset (not estimated)", 0.0
        )

    candidates = detect_markers(markers)
    for event in detect_skeleton(skeleton):
        mapped = map_skeleton_event(event, skeleton, markers, alignment.offset)
        if mapped is not None:
            candidates.append(mapped)
    candidates = add_context(candidates, markers, skeleton, alignment)

    unique = {}
    for event in candidates:
        if not (0 <= event.start <= event.end < markers.frames):
            raise ValueError("A detector returned an invalid C3D interval.")
        if not math.isfinite(event.confidence) or not 0 <= event.confidence <= 1:
            raise ValueError("A detector returned invalid confidence.")
        key = (event.type, event.targets, event.start, event.end)
        if key not in unique or event.confidence > unique[key].confidence:
            unique[key] = event
    events = [e for e in unique.values() if e.confidence >= min_confidence]
    events.sort(key=lambda e: (e.start, e.end, e.type, e.targets))
    return Analysis(markers, skeleton, alignment, events, min_confidence, len(unique))
