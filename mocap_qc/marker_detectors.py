"""Conservative trajectory detectors. Thresholds are in metres and seconds."""

import numpy as np
from .models import Event
from .numerics import curvature, robust_limit, runs


def gaps(take):
    return [
        Event(
            "gap",
            (name,),
            a,
            b,
            1.0,
            f"{b - a + 1} invalid samples ({(b - a + 1) / take.rate:.3f} s): negative/non-finite residual or non-finite XYZ.",
        )
        for j, name in enumerate(take.names)
        for a, b in runs(~take.valid[:, j])
    ]


def frozen_markers(take):
    events = []
    for j, name in enumerate(take.names):
        point = take.positions[:, j]
        still = np.linalg.norm(np.diff(point, axis=0), axis=1) <= 1e-9
        for a, b0 in runs(still):
            b = b0 + 1
            if b - a + 1 < max(6, int(np.ceil(0.08 * take.rate))):
                continue
            distances = np.nanmedian(
                np.linalg.norm(take.positions - point[:, None], axis=2), axis=0
            )
            neighbors = [
                int(k) for k in np.argsort(distances) if k != j and distances[k] < 0.6
            ][:5]
            if len(neighbors) < 2:
                continue
            motion = np.linalg.norm(
                take.positions[b, neighbors] - take.positions[a, neighbors], axis=1
            )
            displacement = float(np.nanmedian(motion))
            boundary_steps = []
            if a > 0:
                boundary_steps.append(np.linalg.norm(point[a] - point[a - 1]))
            if b + 1 < len(point):
                boundary_steps.append(np.linalg.norm(point[b + 1] - point[b]))
            typical_step = float(
                np.nanmedian(np.linalg.norm(np.diff(point, axis=0), axis=1))
            )
            release_jump = max(boundary_steps, default=0) > max(0.015, 8 * typical_step)
            if displacement > 0.03 and release_jump:
                events.append(
                    Event(
                        "frozen_marker",
                        (name,),
                        a,
                        b,
                        0.98,
                        f"XYZ repeats to 1 nm for {b - a + 1} samples while nearby markers move "
                        f"a median {displacement * 1000:.1f} mm between the endpoints, with a discontinuous entry/release. Possible held samples.",
                    )
                )
    return events


def positional_spikes(positions, names, rate, excluded=(), event_type="spike"):
    """Short excursions with opposing entry/exit jumps and quiet neighboring curvature."""
    events = []
    curve = curvature(positions)
    for j, name in enumerate(names):
        p = positions[:, j]
        threshold = robust_limit(curve[:, j], 0.015)
        candidates = []
        starts = sorted(
            {
                int(t + d)
                for t in np.flatnonzero(curve[:, j] > threshold / 2)
                for d in (-1, 0, 1)
            }
        )
        for a in starts:
            for length in range(1, 4):
                b = a + length - 1
                if a < 6 or b + 6 >= len(p) or not np.isfinite(p[a - 6 : b + 7]).all():
                    continue
                if any(
                    name in e.targets and a <= e.end + 1 and b >= e.start - 1
                    for e in excluded
                ):
                    continue
                pre_v = np.median(np.diff(p[a - 6 : a], axis=0), axis=0)
                post_v = np.median(np.diff(p[b + 1 : b + 7], axis=0), axis=0)
                enter = p[a] - p[a - 1] - pre_v
                leave = p[b + 1] - p[b] - post_v
                ne, nl = np.linalg.norm(enter), np.linalg.norm(leave)
                if min(ne, nl) < threshold or max(ne, nl) / min(ne, nl) > 2:
                    continue
                cosine = np.dot(enter, leave) / (ne * nl)
                if cosine > -0.8:
                    continue
                bridge = np.linspace(p[a - 1], p[b + 1], length + 2)[1:-1]
                amplitude = float(np.max(np.linalg.norm(p[a : b + 1] - bridge, axis=1)))
                outer = np.r_[curve[a - 5 : a - 1, j], curve[b + 2 : b + 6, j]]
                if amplitude < threshold or np.max(outer) > max(
                    0.004, 0.25 * amplitude
                ):
                    continue
                if np.linalg.norm(enter + leave) > max(0.005, 0.3 * max(ne, nl)):
                    continue
                candidates.append(
                    (amplitude / (np.mean(outer) + 0.001), a, b, amplitude)
                )
        accepted = []
        for _, a, b, amplitude in sorted(candidates, reverse=True):
            if any(a <= y + 1 and b >= z - 1 for z, y in accepted):
                continue
            accepted.append((a, b))
            events.append(
                Event(
                    event_type,
                    (name,),
                    a,
                    b,
                    0.93 if amplitude >= 2 * threshold else 0.88,
                    f"Short excursion {amplitude * 1000:.1f} mm from the local bridge; "
                    f"opposing entry/exit jumps and quiet surrounding samples "
                    f"(minimum amplitude {threshold * 1000:.1f} mm).",
                )
            )
    return events


def marker_swaps(take):
    """Paired crossings that become continuous when two labels are exchanged."""
    p = take.positions
    predicted = 2 * p[1:-1] - p[:-2]
    error = np.linalg.norm(p[2:] - predicted, axis=2)
    boundaries = {}
    for t0 in np.flatnonzero(np.sum(error > 0.025, axis=1) >= 2):
        t = int(t0 + 2)
        ids = np.flatnonzero(error[t0] > 0.025)
        for ai, a in enumerate(ids):
            for b in ids[ai + 1 :]:
                normal = error[t0, a] + error[t0, b]
                exchanged = np.linalg.norm(p[t, a] - predicted[t0, b]) + np.linalg.norm(
                    p[t, b] - predicted[t0, a]
                )
                if (
                    normal > 0.06
                    and exchanged < 0.20 * normal
                    and np.linalg.norm(p[t - 1, a] - p[t - 1, b]) > 0.03
                ):
                    boundaries.setdefault((int(a), int(b)), []).append(t)
    events = []
    for (a, b), ts in boundaries.items():
        # An entry and a return boundary give a bounded, actionable interval.
        for start, end in zip(ts[::2], ts[1::2]):
            if end - start < 2 or not take.valid[start - 2 : end + 1, [a, b]].all():
                continue
            events.append(
                Event(
                    "label_swap",
                    (take.names[a], take.names[b]),
                    start,
                    end - 1,
                    0.97,
                    "At both interval boundaries, exchanging these two marker labels reduces "
                    "the linear continuation error by at least 80%; the labels return afterward.",
                )
            )
    return events


def marker_discontinuities(take, excluded=()):
    """A sudden position offset between two smooth local tracks; not a speed-only alarm."""
    curve = curvature(take.positions)
    events = []
    for j, name in enumerate(take.names):
        p = take.positions[:, j]
        limit = robust_limit(curve[:, j], 0.008)
        candidates = []
        for t in np.flatnonzero(curve[:, j] > limit):
            for start in (int(t), int(t + 1)):
                if (
                    start < 10
                    or start + 10 > len(p)
                    or not np.isfinite(p[start - 10 : start + 10]).all()
                ):
                    continue
                if any(
                    name in e.targets and e.start - 2 <= start <= e.end + 2
                    for e in excluded
                ):
                    continue
                left = np.arange(-10, 0, dtype=float)
                right = np.arange(0, 10, dtype=float)
                # Quadratic local motion allows genuine acceleration on each side.
                lc = np.polynomial.polynomial.polyfit(left, p[start - 10 : start], 2)
                rc = np.polynomial.polynomial.polyfit(right, p[start : start + 10], 2)
                lv = np.polynomial.polynomial.polyval(-0.5, lc)
                rv = np.polynomial.polynomial.polyval(-0.5, rc)
                jump = float(np.linalg.norm(rv - lv))
                le = (
                    p[start - 10 : start] - np.polynomial.polynomial.polyval(left, lc).T
                )
                re = (
                    p[start : start + 10]
                    - np.polynomial.polynomial.polyval(right, rc).T
                )
                fit_error = float(np.sqrt(np.mean(np.r_[le, re] ** 2)))
                if jump > max(0.018, 12 * fit_error) and fit_error < 0.002:
                    candidates.append(
                        (jump / max(fit_error, 0.0001), start, jump, fit_error)
                    )
        accepted = []
        for _, t, jump, fit in sorted(candidates, reverse=True):
            if any(abs(t - a) <= 3 for a in accepted):
                continue
            accepted.append(t)
            distances = np.linalg.norm(take.positions - p[:, None], axis=2)
            med = np.nanmedian(distances, axis=0)
            mad = 1.4826 * np.nanmedian(np.abs(distances - med), axis=0)
            rigid_ids = np.flatnonzero((med > 0.01) & (med < 0.2) & (mad < 0.0008))
            support = 0
            for k in rigid_ids:
                segment = distances[t - 10 : t + 10, k]
                if not np.isfinite(segment).all():
                    continue
                lc = np.polynomial.polynomial.polyfit(
                    np.arange(-10, 0), segment[:10], 2
                )
                rc = np.polynomial.polynomial.polyfit(np.arange(0, 10), segment[10:], 2)
                if (
                    abs(
                        np.polynomial.polynomial.polyval(-0.5, rc)
                        - np.polynomial.polynomial.polyval(-0.5, lc)
                    )
                    > 0.003
                ):
                    support += 1
            # A discontinuity alone is a review candidate; require clean fits or rigid geometry support.
            confidence = (
                0.88
                if support >= 2
                else (0.86 if fit <= 0.0005 and jump >= 50 * max(fit, 1e-6) else 0.70)
            )
            events.append(
                Event(
                    "marker_discontinuity",
                    (name,),
                    t,
                    t,
                    confidence,
                    f"Estimated position step {jump * 1000:.1f} mm between locally smooth tracks "
                    f"(fit RMS {fit * 1000:.2f} mm; {support} stable-distance references corroborate it). "
                    "The cause and which side is correct require review.",
                )
            )
    return events


def detect_markers(take):
    found = gaps(take) + frozen_markers(take) + marker_swaps(take)
    found += positional_spikes(take.positions, take.names, take.rate, found)
    found += marker_discontinuities(take, found)
    return found
