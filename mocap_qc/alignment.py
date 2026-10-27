"""Constant time-offset estimation using a pelvis cluster and the skeleton root."""

import numpy as np
from .models import Alignment


def marker_indices(names, labels):
    lookup = {}
    for i, name in enumerate(names):
        lookup.setdefault(name.rsplit(":", 1)[-1].upper(), []).append(i)
    return [lookup[label][0] for label in labels if len(lookup.get(label, [])) == 1]


def pelvis_center(markers):
    for labels in [
        ("LFWT", "LMWT", "LBWT", "RFWT", "RMWT", "RBWT"),
        ("LASI", "RASI", "LPSI", "RPSI"),
    ]:
        ids = marker_indices(markers.names, labels)
        if len(ids) >= 4:
            points = markers.positions[:, ids]
            valid = markers.valid[:, ids].all(axis=1)
            result = np.full((markers.frames, 3), np.nan)
            result[valid] = points[valid].mean(axis=1)
            return result, [markers.names[i] for i in ids]
    raise ValueError(
        "Automatic synchronization needs an unambiguous pelvis marker set "
        "(LFWT/LMWT/LBWT/RFWT/RMWT/RBWT or LASI/RASI/LPSI/RPSI). "
        "Use --offset-frames when the timing is known."
    )


def root_index(skeleton):
    roots = np.flatnonzero(skeleton.parents < 0)
    if len(roots) != 1:
        raise ValueError(
            "Automatic synchronization requires exactly one skeleton root."
        )
    return int(roots[0])


def fit_velocity_rotation(source, target):
    """A proper rotation, with the worst 10% of pairs trimmed (no scaling or time warp)."""
    good = np.isfinite(source).all(axis=1) & np.isfinite(target).all(axis=1)
    if good.sum() < 30:
        return np.inf, np.eye(3)
    a, b = source[good], target[good]
    keep = np.ones(len(a), dtype=bool)
    for _ in range(3):
        u, _, vt = np.linalg.svd(a[keep].T @ b[keep])
        fix = np.eye(3)
        fix[-1, -1] = np.linalg.det(u @ vt)
        rotation = u @ fix @ vt
        residual = np.linalg.norm(a @ rotation - b, axis=1)
        keep = residual <= np.quantile(residual, 0.90)
    return float(np.mean(residual[keep])), rotation


def estimate_alignment(markers, skeleton, max_offset=120):
    if max_offset < 1 or max_offset >= markers.frames // 2:
        raise ValueError(
            "--max-offset-frames must be positive and below half the C3D length."
        )
    pelvis, used = pelvis_center(markers)
    root = skeleton.positions[:, root_index(skeleton)]
    if not np.isfinite(root).all():
        raise ValueError(
            "Non-finite root samples prevent automatic synchronization; use --offset-frames."
        )
    ticks = np.arange(int(np.floor(skeleton.times[-1] * markers.rate + 1e-7)) + 1)
    source = np.column_stack(
        [np.interp(ticks / markers.rate, skeleton.times, root[:, k]) for k in range(3)]
    )
    source_v = np.diff(source, axis=0) * markers.rate
    target_v = np.diff(pelvis, axis=0) * markers.rate
    records = []
    rotations = {}
    for offset in range(-max_offset, max_offset + 1):
        idx = np.arange(max(0, -offset), min(len(source_v), len(target_v) - offset))
        if len(idx) < max(30, int(0.5 * min(len(source_v), len(target_v)))):
            continue
        a, b = source_v[idx], target_v[idx + offset]
        error, rotation = fit_velocity_rotation(a, b)
        middle = len(idx) // 2
        first, _ = fit_velocity_rotation(a[:middle], b[:middle])
        second, _ = fit_velocity_rotation(a[middle:], b[middle:])
        records.append((offset, error, first, second))
        rotations[offset] = rotation
    records.sort(key=lambda x: x[1])
    if len(records) < 2 or not np.isfinite(records[0][1]):
        raise ValueError(
            "Not enough overlapping valid samples to synchronize the takes."
        )
    best, error, _, _ = records[0]
    speed_scale = float(np.nanmedian(np.linalg.norm(target_v, axis=1)))
    spread = float(np.nanstd(np.linalg.norm(target_v, axis=1)))
    margin = (records[1][1] - error) / max(error, 1e-9)
    half_offsets = [min(records, key=lambda row: row[i])[0] for i in (2, 3)]
    if (
        speed_scale < 0.005
        or spread < 0.002
        or abs(best) == max_offset
        or margin < 0.02
        or error / max(speed_scale, 0.001) > 0.5
        or any(abs(k - best) > 2 for k in half_offsets)
    ):
        raise ValueError(
            "Automatic timing is ambiguous (static/repetitive motion, boundary hit, "
            "or inconsistent windows). Supply a verified --offset-frames value "
            "or increase --max-offset-frames; no default zero is assumed."
        )
    score = float(np.clip(1 - error / max(speed_scale, 1e-9), 0, 1))
    return Alignment(
        int(best),
        "Robust pelvis/root velocity alignment",
        score,
        {
            "pelvis_markers": used,
            "search_range_frames": [-max_offset, max_offset],
            "velocity_error_m_per_s": error,
            "runner_up_offset": int(records[1][0]),
            "runner_up_relative_error_increase": margin,
            "half_window_offsets": half_offsets,
            "usd_to_c3d_velocity_rotation": rotations[best].tolist(),
            "note": "Spatial rotation is fitted for timing only; marker and joint origins need not coincide.",
        },
    )
