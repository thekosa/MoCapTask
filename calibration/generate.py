"""Generate paired synthetic C3D/USD fixtures with exact injected-event labels.

The samples are deliberately synthetic: they provide reproducible positive and
negative controls, not a substitute for expert labels on real captures.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from mocap_qc.readers import native_path


DATA = Path(__file__).resolve().parent / "data"
RATE = 120
FRAMES = 480

MARKERS = (
    "A1:LFWT",
    "A1:LMWT",
    "A1:LBWT",
    "A1:RFWT",
    "A1:RMWT",
    "A1:RBWT",
    "A1:LFHD",
    "A1:RTOE",
    "A1:LELB",
    "A1:LIWR",
    "A1:LOWR",
    "A1:RRNG6",
    "A1:T145_cluster_LCM_5",
)
JOINTS = (
    "Hips",
    "Hips/Spine",
    "Hips/Spine/LeftForeArm",
    "Hips/Spine/RightForeArm",
)
PELVIS_OFFSETS = np.asarray(
    [
        [-0.10, 0.00, 0.00],
        [-0.10, 0.02, 0.00],
        [-0.10, -0.02, 0.00],
        [0.10, 0.00, 0.00],
        [0.10, 0.02, 0.00],
        [0.10, -0.02, 0.00],
    ]
)
BODY_OFFSETS = {
    "A1:LFHD": (-0.04, 0.27, 0.55),
    "A1:RTOE": (0.15, -0.78, 0.10),
    "A1:LELB": (-0.42, 0.13, 0.32),
    "A1:LIWR": (-0.55, -0.02, 0.28),
    "A1:LOWR": (-0.45, -0.02, 0.28),
    "A1:RRNG6": (0.31, 0.24, 0.36),
    "A1:T145_cluster_LCM_5": (0.00, 0.34, 0.35),
}


def output_path(path: Path) -> str:
    """Give native libraries an ASCII parent path on Windows when available."""
    return str(Path(native_path(path.parent)) / path.name)


def root_track(variant: int, fast: bool = False) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(FRAMES, dtype=float) / RATE
    phase = 0.37 if variant == 0 else 1.11
    # Smooth, multi-frequency motion with a different phase per held-out take.
    root = np.column_stack(
        (
            0.31 * np.sin(0.83 * t + phase) + 0.055 * np.sin(2.7 * t + 0.2),
            0.22 * np.cos(0.61 * t - phase) + 0.045 * np.sin(1.9 * t),
            0.94 + 0.035 * np.sin(0.47 * t + phase) + 0.02 * np.cos(1.4 * t),
        )
    )
    if variant == 1:
        root += np.column_stack(
            (
                0.025 * np.sin(4.1 * t + 0.6),
                0.018 * np.cos(3.2 * t),
                0.012 * np.sin(3.8 * t + 0.4),
            )
        )
    if fast:
        root += np.column_stack(
            (
                0.035 * np.sin(5.2 * t),
                0.022 * np.cos(4.3 * t),
                0.018 * np.sin(3.7 * t),
            )
        )
    return t, root


def clean_marker_positions(variant: int, fast: bool = False) -> np.ndarray:
    t, root = root_track(variant, fast=fast)
    positions = np.empty((FRAMES, len(MARKERS), 3), dtype=float)
    positions[:, :6] = root[:, None, :] + PELVIS_OFFSETS[None, :, :]
    for j, name in enumerate(MARKERS[6:], start=6):
        offset = np.asarray(BODY_OFFSETS[name], dtype=float)
        phase = 0.43 * j + 0.25 * variant
        local = np.column_stack(
            (
                0.018 * np.sin((1.1 + 0.08 * j) * t + phase),
                0.014 * np.cos((0.9 + 0.05 * j) * t - phase),
                0.012 * np.sin((1.4 + 0.04 * j) * t + 0.5 * phase),
            )
        )
        if name in ("A1:LIWR", "A1:LOWR", "A1:LELB"):
            local[:, 0] += 0.035 * np.sin(2.2 * t + phase)
            local[:, 1] += 0.045 * np.cos(1.7 * t + phase)
        positions[:, j] = root + offset + local
    return positions


def write_c3d(path: Path, positions: np.ndarray, invalid: dict[str, tuple[int, int]]) -> None:
    import ezc3d

    c3d = ezc3d.c3d()
    c3d["parameters"]["POINT"]["RATE"]["value"] = [float(RATE)]
    c3d["parameters"]["POINT"]["UNITS"]["value"] = ["mm"]
    c3d["parameters"]["POINT"]["LABELS"]["value"] = list(MARKERS)
    points = np.zeros((4, len(MARKERS), FRAMES), dtype=float)
    points[:3] = positions.transpose(2, 1, 0) * 1000.0
    residuals = np.zeros((1, len(MARKERS), FRAMES), dtype=float)
    for marker, (start, end) in invalid.items():
        j = MARKERS.index(marker)
        residuals[0, j, start : end + 1] = -1.0
    c3d["data"]["points"] = points
    c3d["data"]["meta_points"]["residuals"] = residuals
    path.parent.mkdir(parents=True, exist_ok=True)
    c3d.write(output_path(path))


def write_usd(
    path: Path,
    variant: int,
    root_spike: tuple[int, int] | None,
    rotation_excursion: tuple[int, int] | None,
    bone_change: tuple[int, int] | None,
    fast: bool = False,
) -> None:
    from pxr import Gf, Usd, UsdGeom, UsdSkel, Vt

    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(output_path(path))
    stage.SetTimeCodesPerSecond(float(RATE))
    stage.SetFramesPerSecond(float(RATE))
    stage.SetStartTimeCode(0.0)
    stage.SetEndTimeCode(float(FRAMES - 1))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root = UsdSkel.Root.Define(stage, "/Actor")
    skeleton = UsdSkel.Skeleton.Define(stage, "/Actor/Skeleton")
    skeleton.CreateJointsAttr(Vt.TokenArray(list(JOINTS)))
    skeleton.CreateRestTransformsAttr(
        Vt.Matrix4dArray([Gf.Matrix4d(1) for _ in JOINTS])
    )
    skeleton.CreateBindTransformsAttr(
        Vt.Matrix4dArray([Gf.Matrix4d(1) for _ in JOINTS])
    )
    animation = UsdSkel.Animation.Define(stage, "/Actor/Animation")
    animation.CreateJointsAttr(Vt.TokenArray(list(JOINTS)))
    binding = UsdSkel.BindingAPI.Apply(skeleton.GetPrim())
    binding.CreateAnimationSourceRel().SetTargets([animation.GetPath()])

    translations_attr = animation.CreateTranslationsAttr()
    rotations_attr = animation.CreateRotationsAttr()
    scales_attr = animation.CreateScalesAttr()
    _, root_positions = root_track(variant, fast=fast)
    for frame in range(FRAMES):
        local_translations = [
            root_positions[frame].copy(),
            np.asarray([0.0, 0.0, 0.24]),
            np.asarray([-0.34, 0.0, 0.17]),
            np.asarray([0.34, 0.0, 0.17]),
        ]
        if root_spike and root_spike[0] <= frame <= root_spike[1]:
            local_translations[0] = local_translations[0] + np.asarray([0.055, -0.015, 0.01])
        if bone_change and bone_change[0] <= frame <= bone_change[1]:
            local_translations[2] = local_translations[2] + np.asarray([0.025, 0.0, 0.0])

        joint_rotations = [Gf.Quatf(1.0, Gf.Vec3f(0.0, 0.0, 0.0)) for _ in JOINTS]
        if rotation_excursion and rotation_excursion[0] <= frame <= rotation_excursion[1]:
            joint_rotations[3] = Gf.Quatf(0.0, Gf.Vec3f(1.0, 0.0, 0.0))

        time_code = float(frame)
        translations_attr.Set(
            Vt.Vec3fArray([Gf.Vec3f(*map(float, p)) for p in local_translations]),
            time_code,
        )
        rotations_attr.Set(Vt.QuatfArray(joint_rotations), time_code)
        scales_attr.Set(
            Vt.Vec3hArray([Gf.Vec3h(1.0, 1.0, 1.0) for _ in JOINTS]),
            time_code,
        )
    stage.GetRootLayer().Save()


def make_case(split: str, variant: int, case_name: str) -> dict:
    fast_motion = case_name == "clean_fast"
    positions = clean_marker_positions(variant, fast=fast_motion)
    invalid: dict[str, tuple[int, int]] = {}
    root_spike = rotation_excursion = bone_change = None
    known_events: list[dict] = []
    notes = "Clean analytic baseline; no injected defects."

    if case_name == "gap":
        invalid["A1:RTOE"] = (120, 150)
        known_events = [{"type": "gap", "targets": ["A1:RTOE"], "start": 120, "end": 150}]
        notes = "Negative C3D residual injected for the inclusive interval."
    elif case_name == "frozen_marker":
        j = MARKERS.index("A1:LELB")
        positions[120:181, j] = positions[120, j]
        known_events = [{"type": "frozen_marker", "targets": ["A1:LELB"], "start": 120, "end": 180}]
        notes = "A marker track is held at one coordinate for 61 samples."
    elif case_name in ("spike_small", "spike_large"):
        j = MARKERS.index("A1:LFHD")
        delta = np.asarray([0.020, -0.010, 0.0]) if case_name == "spike_small" else np.asarray([0.045, -0.020, 0.010])
        positions[160:162, j] += delta
        known_events = [{"type": "spike", "targets": ["A1:LFHD"], "start": 160, "end": 161}]
        notes = f"A two-frame displacement of {np.linalg.norm(delta) * 1000:.1f} mm is injected."
    elif case_name == "label_swap":
        a, b = MARKERS.index("A1:LIWR"), MARKERS.index("A1:LOWR")
        positions[150:211, [a, b]] = positions[150:211, [b, a]]
        known_events = [{"type": "label_swap", "targets": ["A1:LIWR", "A1:LOWR"], "start": 150, "end": 210}]
        notes = "Two marker labels are exchanged for an inclusive 61-frame interval."
    elif case_name == "marker_step":
        j = MARKERS.index("A1:RRNG6")
        positions[240:, j] += np.asarray([0.025, 0.005, -0.010])
        known_events = [{"type": "marker_discontinuity", "targets": ["A1:RRNG6"], "start": 240, "end": 240}]
        notes = "A persistent 27.4 mm marker position step is injected at the boundary."
    elif case_name == "marker_step_soft":
        j = MARKERS.index("A1:RRNG6")
        rng = np.random.default_rng(713 + variant)
        positions[:, j] += rng.normal(0.0, 0.00065, size=(FRAMES, 3))
        positions[240:, j] += np.asarray([0.022, 0.0, 0.0])
        known_events = [{"type": "marker_discontinuity", "targets": ["A1:RRNG6"], "start": 240, "end": 240}]
        notes = "A 22 mm step is injected over 0.65 mm measurement jitter; it tests a low-score true positive."
    elif case_name == "root_spike":
        root_spike = (200, 200)
        known_events = [{"type": "skeleton_translation_spike", "targets": ["Hips"], "start": 200, "end": 200}]
        notes = "A one-sample root translation excursion is injected into the USD animation."
    elif case_name == "rotation_excursion":
        rotation_excursion = (170, 185)
        known_events = [{"type": "rotation_excursion", "targets": ["Hips/Spine/RightForeArm"], "start": 170, "end": 185}]
        notes = "The right forearm local orientation makes a 180-degree excursion and returns."
    elif case_name == "bone_length_change":
        bone_change = (240, 250)
        known_events = [{"type": "bone_length_change", "targets": ["Hips/Spine", "Hips/Spine/LeftForeArm"], "start": 240, "end": 250}]
        notes = "The left forearm local translation changes by 25 mm for 11 samples."
    elif case_name == "clean_fast":
        notes = "Clean, smooth fast-motion negative control; no defect is injected."
    elif case_name != "clean_smooth":
        raise ValueError(f"Unknown case: {case_name}")

    case_id = f"{split}_{case_name}"
    case_dir = DATA / split
    c3d_path = case_dir / f"{case_name}.c3d"
    usd_path = case_dir / f"{case_name}.usdc"
    write_c3d(c3d_path, positions, invalid)
    write_usd(usd_path, variant, root_spike, rotation_excursion, bone_change, fast=fast_motion)
    return {
        "case_id": case_id,
        "split": split,
        "motion_id": f"motion_variant_{variant}",
        "kind": "negative_control" if not known_events else "injected_defect",
        "c3d": c3d_path.relative_to(Path(__file__).resolve().parent).as_posix(),
        "usd": usd_path.relative_to(Path(__file__).resolve().parent).as_posix(),
        "rate_hz": RATE,
        "frames": FRAMES,
        "offset_frames": 0,
        "known_events": known_events,
        "notes": notes,
    }


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    cases = []
    names = (
        "clean_smooth",
        "clean_fast",
        "gap",
        "frozen_marker",
        "spike_small",
        "spike_large",
        "label_swap",
        "marker_step",
        "root_spike",
        "rotation_excursion",
        "bone_length_change",
        "marker_step_soft",
    )
    for split, variant in (("development", 0), ("heldout", 1)):
        for name in names:
            cases.append(make_case(split, variant, name))
    manifest = {
        "schema_version": 1,
        "description": "Paired synthetic C3D/USD calibration corpus with exact labels for injected defects.",
        "units": "C3D millimetres; USD metres",
        "sampling": {"rate_hz": RATE, "frames": FRAMES, "duration_seconds": FRAMES / RATE},
        "split_policy": "development and heldout use different analytic motion variants; no source take is shared across splits.",
        "matching_policy": {
            "same_type_and_targets_required": True,
            "point_event_tolerance_frames": 1,
            "interval_event_iou_minimum": 0.5,
        },
        "limitations": [
            "The baselines are analytic motion, not expert-cleaned human captures.",
            "Injected events provide exact type/target/frame labels but do not reproduce all real capture faults.",
            "Results are a reproducible smoke-calibration study, not a real-world precision/recall claim.",
        ],
        "cases": cases,
    }
    (Path(__file__).resolve().parent / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(cases)} paired cases ({len(cases) * 2} input files) under {DATA}")


if __name__ == "__main__":
    main()
