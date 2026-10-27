"""Input adapters. Neither reader modifies or exports the input files."""
import ctypes
import os
from pathlib import Path

import numpy as np

from .models import MarkerTake, SkeletonTake


def native_path(path):
    """Work around OpenUSD's Windows Unicode-path limitation without copying data."""
    path = str(Path(path).resolve(strict=True))
    if os.name == 'nt' and not path.isascii():
        get_short = ctypes.windll.kernel32.GetShortPathNameW
        get_short.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        get_short.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32768)
        length = get_short(path, buffer, len(buffer))
        if 0 < length < len(buffer) and buffer.value.isascii():
            return buffer.value
    return path


def read_c3d(path):
    import ezc3d
    raw = ezc3d.c3d(native_path(path))
    point = raw['parameters']['POINT']
    units = str(point['UNITS']['value'][0]).strip().lower()
    factors = {'mm': 0.001, 'cm': 0.01, 'm': 1.0}
    if units not in factors:
        raise ValueError(f'Unsupported C3D POINT:UNITS {units!r}; expected mm, cm or m.')
    rate = float(point['RATE']['value'][0])
    if not np.isfinite(rate) or rate <= 0:
        raise ValueError('C3D point rate must be positive and finite.')
    names = []
    for key in ['LABELS'] + [f'LABELS{i}' for i in range(2, 20)]:
        if key in point:
            names.extend(str(x).strip() for x in point[key]['value'])
    positions = raw['data']['points'][:3].transpose(2, 1, 0).copy() * factors[units]
    residuals = raw['data']['meta_points']['residuals'][0].T
    if len(names) != positions.shape[1] or len(set(names)) != len(names) or any(not n for n in names):
        raise ValueError('C3D marker names must be present, unique, and match the point count.')
    if len(positions) < 3:
        raise ValueError('At least three C3D frames are required.')
    # Zero residual means processed/estimated data, not a missing point.
    valid = np.isfinite(positions).all(axis=2) & np.isfinite(residuals) & (residuals >= 0)
    positions[~valid] = np.nan
    return MarkerTake(tuple(names), positions, valid, rate, {
        'file': Path(path).name, 'units': units, 'rate': rate,
        'frames': len(positions), 'markers': len(names),
        'first_frame_in_ezc3d': int(raw['header']['points']['first_frame']),
        'negative_residual_samples': int(np.sum(residuals < 0)),
        'zero_residual_samples': int(np.sum(residuals == 0)),
        'valid_samples': int(valid.sum()),
        'axes': 'C3D axes retained; geometric distances and speeds are rotation invariant',
    })


def read_usd(path):
    from pxr import Usd, UsdGeom, UsdSkel
    try:
        stage = Usd.Stage.Open(native_path(path))
    except Exception as exc:
        raise ValueError('Cannot open USD. On Windows with non-ASCII paths, enable short '
                         'path names or run a copy of the whole project from an ASCII path. '
                         f'OpenUSD detail: {exc}') from exc
    if not stage or stage.GetCompositionErrors():
        raise ValueError('USD stage could not be fully composed; check referenced assets.')
    skeletons = [UsdSkel.Skeleton(p) for p in stage.Traverse() if p.IsA(UsdSkel.Skeleton)]
    if len(skeletons) != 1:
        raise ValueError(f'Expected one UsdSkel Skeleton, found {len(skeletons)}.')
    skeleton = skeletons[0]
    cache = UsdSkel.Cache()
    for p in stage.Traverse():
        if p.IsA(UsdSkel.Root):
            cache.Populate(UsdSkel.Root(p), Usd.PrimDefaultPredicate)
    query = cache.GetSkelQuery(skeleton)
    if not query or not query.GetAnimQuery():
        raise ValueError('Skeleton needs an animation binding inside a SkelRoot.')
    names = tuple(str(n) for n in query.GetJointOrder())
    parents = np.asarray(query.GetTopology().GetParentIndices(), dtype=int)
    if not names or len(set(names)) != len(names):
        raise ValueError('USD joint names must be nonempty and unique.')
    time_codes = np.asarray(query.GetAnimQuery().GetJointTransformTimeSamples(), dtype=float)
    if len(time_codes) < 3 or not np.isfinite(time_codes).all():
        raise ValueError('USD requires at least three finite authored pose sample times.')
    if not np.allclose(np.diff(time_codes), np.diff(time_codes)[0], rtol=1e-6, atol=1e-9):
        raise ValueError('Irregular USD pose sampling is not supported by this take-home tool.')
    tcps = stage.GetTimeCodesPerSecond()
    unit = UsdGeom.GetStageMetersPerUnit(stage)
    if not np.isfinite([tcps, unit]).all() or tcps <= 0 or unit <= 0:
        raise ValueError('USD timeCodesPerSecond and metersPerUnit must be positive and finite.')
    times = (time_codes - time_codes[0]) / tcps
    shape = (len(times), len(names), 3)
    world = np.empty(shape)
    local = np.empty(shape)
    rotations = np.empty(shape[:2] + (4,))
    scales = np.empty(shape)
    xform_cache = UsdGeom.XformCache()
    for f, code in enumerate(time_codes):
        time = Usd.TimeCode(float(code))
        transforms = query.ComputeJointLocalTransforms(time)
        if len(transforms) != len(names):
            raise ValueError(f'USD local transform count does not match joints at {code}.')
        trans, rot, scale = UsdSkel.DecomposeTransforms(transforms)
        local[f] = np.asarray(trans) * unit
        rotations[f] = np.asarray(rot)  # Vt buffer layout is xyzw, despite repr being wxyz.
        scales[f] = np.asarray(scale)
        xform_cache.SetTime(time)
        prim_world = np.asarray(xform_cache.GetLocalToWorldTransform(skeleton.GetPrim()))
        joint_skel = np.asarray(query.ComputeJointSkelTransforms(time))
        world[f] = (joint_skel @ prim_world)[:, 3, :3] * unit
    return SkeletonTake(names, parents, times, world, local, rotations, scales, {
        'file': Path(path).name, 'prim': str(skeleton.GetPath()), 'joints': len(names),
        'samples': len(times), 'start_time_code': float(time_codes[0]),
        'end_time_code': float(time_codes[-1]), 'time_codes_per_second': float(tcps),
        'frames_per_second': float(stage.GetFramesPerSecond()),
        'meters_per_unit': float(unit), 'up_axis': str(UsdGeom.GetStageUpAxis(stage)),
        'units_authored': bool(UsdGeom.StageHasAuthoredMetersPerUnit(stage)),
        'axis_authored': stage.HasAuthoredMetadata('upAxis'),
        'sample_rate': 1.0 / float(times[1] - times[0]),
        'local_rotation_convention': 'xyzw, joint-local; q and -q represent the same rotation',
    })
