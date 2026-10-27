from pathlib import Path
import numpy as np
import pytest
from mocap_qc.readers import native_path, read_c3d, read_usd


def output_path(path):
    return str(Path(native_path(path.parent)) / path.name)


@pytest.mark.parametrize("units,factor", [("mm", 0.001), ("cm", 0.01), ("m", 1.0)])
def test_c3d_units_and_invalid_samples(tmp_path, units, factor):
    import ezc3d

    path = tmp_path / "sample.c3d"
    c = ezc3d.c3d()
    c["parameters"]["POINT"]["RATE"]["value"] = [120.0]
    c["parameters"]["POINT"]["UNITS"]["value"] = [units]
    c["parameters"]["POINT"]["LABELS"]["value"] = ["A", "B"]
    points = np.zeros((4, 2, 20))
    points[0] = 10
    c["data"]["points"] = points
    residuals = np.zeros((1, 2, 20))
    residuals[0, 0, 5:8] = -1
    c["data"]["meta_points"]["residuals"] = residuals
    c.write(output_path(path))
    m = read_c3d(path)
    assert np.allclose(m.positions[:5, :, 0], 10 * factor)
    assert np.flatnonzero(~m.valid[:, 0]).tolist() == [5, 6, 7]
    assert m.valid[
        :, 1
    ].all()  # residual zero, and XYZ components zero, are legitimate.
    assert m.names == ("A", "B")


def test_usd_applies_hierarchy_prim_transform_units_and_animation_order(tmp_path):
    from pxr import Usd, UsdGeom, UsdSkel, Gf, Vt

    stage = Usd.Stage.CreateInMemory()
    stage.SetTimeCodesPerSecond(60)
    stage.SetFramesPerSecond(24)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdSkel.Root.Define(stage, "/Actor")
    UsdGeom.Xformable(root).AddTranslateOp().Set(Gf.Vec3d(100, 0, 0))
    skel = UsdSkel.Skeleton.Define(stage, "/Actor/Skeleton")
    skel.CreateJointsAttr(Vt.TokenArray(["Root", "Root/Child"]))
    skel.CreateRestTransformsAttr(Vt.Matrix4dArray([Gf.Matrix4d(1), Gf.Matrix4d(1)]))
    anim = UsdSkel.Animation.Define(stage, "/Actor/Anim")
    anim.CreateJointsAttr(
        Vt.TokenArray(["Root/Child", "Root"])
    )  # Intentionally reordered.
    for t in (10.0, 11.0, 12.0):
        anim.CreateTranslationsAttr().Set(Vt.Vec3fArray([(0, 10, 0), (t, 0, 0)]), t)
        anim.CreateRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(1), Gf.Quatf(1)]), t)
        anim.CreateScalesAttr().Set(Vt.Vec3hArray([(1, 1, 1), (1, 1, 1)]), t)
    UsdSkel.BindingAPI.Apply(skel.GetPrim()).CreateAnimationSourceRel().SetTargets(
        [anim.GetPath()]
    )
    path = tmp_path / "sample.usda"
    stage.GetRootLayer().Export(output_path(path))
    s = read_usd(path)
    assert s.names == ("Root", "Root/Child")
    assert np.allclose(s.positions[0], [[1.1, 0, 0], [1.1, 0.1, 0]])
    assert np.allclose(s.local_positions[0], [[0.1, 0, 0], [0, 0.1, 0]])
    assert np.allclose(s.times, [0, 1 / 60, 2 / 60])
    assert s.metadata["frames_per_second"] == 24
