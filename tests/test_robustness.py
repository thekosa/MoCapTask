import numpy as np
import pytest

from conftest import make_markers, make_skeleton
from mocap_qc.marker_detectors import detect_markers
from mocap_qc.skeleton_detectors import detect_skeleton


@pytest.mark.parametrize("noise", [0.0002, 0.001])
@pytest.mark.parametrize("amplitude", [0.020, 0.045])
def test_isolated_spike_on_noisy_controlled_motion(noise, amplitude):
    m = make_markers(frames=720)
    rng = np.random.default_rng(412)
    m.positions += rng.normal(0, noise, m.positions.shape)
    assert [e for e in detect_markers(m) if e.confidence >= 0.8] == []
    m.positions[300, 0, 0] += amplitude
    reported = [e for e in detect_markers(m) if e.confidence >= 0.8]
    assert [(e.type, e.start, e.end, e.targets) for e in reported] == [
        ("spike", 300, 300, ("A1:P0",))
    ]


def test_smooth_fast_rotation_is_not_a_jump():
    s = make_skeleton()
    angles = np.deg2rad(np.arange(len(s.times)) * 20)
    s.rotations[:, 1, 0] = np.sin(angles / 2)
    s.rotations[:, 1, 3] = np.cos(angles / 2)
    assert detect_skeleton(s) == []


def test_invalid_joint_has_exact_bounds():
    s = make_skeleton()
    s.rotations[30:34, 1] = 0
    events = detect_skeleton(s)
    assert [(e.type, e.start, e.end) for e in events] == [("invalid_joint", 30, 33)]
