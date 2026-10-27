import numpy as np
import pytest
from conftest import make_markers, make_skeleton, trajectory
from mocap_qc.alignment import estimate_alignment

NAMES = ("LFWT", "LMWT", "LBWT", "RFWT", "RMWT", "RBWT")


@pytest.mark.parametrize(
    "offset,skel_rate", [(18, 120), (-12, 120), (0, 120), (18, 60)]
)
def test_known_offset_with_different_axes_origin_and_optional_rate(offset, skel_rate):
    m = make_markers(frames=900)
    m.names = tuple("A1:" + n for n in NAMES)
    offsets = np.array(
        [
            [0.1, 0, 0],
            [-0.1, 0, 0],
            [0, 0.1, 0],
            [0, -0.1, 0],
            [0, 0, 0.1],
            [0, 0, -0.1],
        ]
    )
    m.positions = trajectory(np.arange(m.frames) / m.rate)[:, None] + offsets
    s = make_skeleton(frames=int(900 * skel_rate / 120), rate=skel_rate)
    rotation = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    s.positions[:, 0] = (trajectory(s.times + offset / m.rate) - [2, 3, 4]) @ rotation.T
    s.positions[150, 0] += [0.1, 0, 0]  # A root defect must not decide the alignment.
    result = estimate_alignment(m, s, max_offset=40)
    assert result.offset == offset
    assert all(abs(o - offset) <= 1 for o in result.details["half_window_offsets"])


def test_static_motion_fails_clearly_instead_of_guessing_zero():
    m = make_markers()
    m.names = tuple("A1:" + n for n in NAMES)
    m.positions[:] = m.positions[0]
    s = make_skeleton()
    s.positions[:] = s.positions[0]
    with pytest.raises(ValueError, match="ambiguous"):
        estimate_alignment(m, s, max_offset=30)


def test_unknown_marker_set_requires_manual_timing():
    with pytest.raises(ValueError, match="offset-frames"):
        estimate_alignment(make_markers(), make_skeleton(), max_offset=30)
