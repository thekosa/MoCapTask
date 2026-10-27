"""Small shared numerical helpers; array indices always refer to samples, not timecodes."""
import numpy as np
from .models import Event


def runs(mask):
    indices = np.flatnonzero(mask)
    return [(int(a[0]), int(a[-1])) for a in np.split(indices, np.where(np.diff(indices) > 1)[0] + 1) if len(a)]


def robust_limit(values, floor, multiplier=12):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    if not len(values):
        return float(floor)
    med = np.median(values)
    mad = 1.4826 * np.median(np.abs(values - med))
    return float(max(floor, med + multiplier * mad))


def curvature(points):
    result = np.full(points.shape[:-1], np.nan)
    result[1:-1] = np.linalg.norm(points[1:-1] - .5 * (points[:-2] + points[2:]), axis=-1)
    return result


def angular_steps(quaternions):
    """Shortest physical angle; q/-q and Euler angle wrapping cannot make a false jump."""
    norms = np.linalg.norm(quaternions, axis=-1, keepdims=True)
    q = np.divide(quaternions, norms, out=np.full_like(quaternions, np.nan), where=norms > 1e-12)
    dot = np.sum(q[1:] * q[:-1], axis=-1)
    return np.rad2deg(2 * np.arccos(np.clip(np.abs(dot), 0, 1)))


def map_skeleton_event(event, skeleton, markers, offset):
    # Nearest C3D sample; half frames round upward. Clip to the common recorded interval.
    start = int(np.floor(skeleton.times[event.start] * markers.rate + .5)) + offset
    end = int(np.floor(skeleton.times[event.end] * markers.rate + .5)) + offset
    if end < 0 or start >= markers.frames:
        return None
    clipped_start, clipped_end = max(0, start), min(markers.frames - 1, end)
    note = event.note
    if (clipped_start, clipped_end) != (start, end):
        note += ' Interval clipped to the available C3D frames.'
    return Event(event.type, event.targets, clipped_start, clipped_end, event.confidence, note)
