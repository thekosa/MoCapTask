import numpy as np
import pytest
from conftest import make_markers
from mocap_qc.marker_detectors import (
    detect_markers,
    gaps,
    frozen_markers,
    positional_spikes,
    marker_swaps,
    marker_discontinuities,
)


@pytest.mark.parametrize("length", [1, 2, 3])
def test_short_spikes_have_exact_bounds(length):
    m = make_markers()
    m.positions[140 : 140 + length, 0] += [0.045, -0.02, 0.01]
    found = positional_spikes(m.positions, m.names, m.rate)
    assert [(e.start, e.end, e.targets) for e in found] == [
        (140, 139 + length, ("A1:P0",))
    ]


def test_missing_samples_are_one_inclusive_gap_without_spike_neighbors():
    m = make_markers()
    m.positions[40:46, 0] = np.nan
    m.valid[40:46, 0] = False
    events = detect_markers(m)
    assert [(e.type, e.start, e.end) for e in events if e.confidence >= 0.8] == [
        ("gap", 40, 45)
    ]


def test_frozen_marker_requires_moving_neighbors_and_a_discontinuous_boundary():
    m = make_markers()
    m.positions[120:181, 0] = m.positions[120, 0]
    assert [(e.start, e.end) for e in frozen_markers(m)] == [(120, 180)]


def test_stationary_take_and_planted_marker_are_not_freezes():
    m = make_markers()
    m.positions[:, 0] = [
        0,
        0,
        0,
    ]  # A fixed point next to moving markers is not automatically bad.
    assert frozen_markers(m) == []
    m.positions[:] = m.positions[0]
    assert detect_markers(m) == []


def test_swapped_labels_return_as_one_interval():
    m = make_markers()
    m.positions[100:161, [0, 3]] = m.positions[100:161, [3, 0]]
    result = marker_swaps(m)
    assert len(result) == 1
    assert (result[0].start, result[0].end, result[0].targets) == (
        100,
        160,
        ("A1:P0", "A1:P3"),
    )


def test_natural_marker_crossing_is_not_a_label_swap():
    m = make_markers(count=2)
    t = np.linspace(-1, 1, m.frames)
    m.positions[:, 0] = np.column_stack((t, np.zeros_like(t), np.ones_like(t)))
    m.positions[:, 1] = np.column_stack((-t, np.zeros_like(t), np.ones_like(t)))
    assert marker_swaps(m) == []


def test_clean_position_step_is_detected():
    m = make_markers()
    m.positions[200:, 0] += [0.03, 0, 0]
    result = marker_discontinuities(m)
    assert any(e.start == 200 and e.confidence >= 0.8 for e in result)


@pytest.mark.parametrize("frequency", [3, 8, 15])
def test_fast_smooth_motion_is_not_an_anomaly(frequency):
    m = make_markers(frames=720)
    t = np.arange(m.frames) / m.rate
    m.positions[:, :, 0] += 0.1 * np.sin(frequency * t)[:, None]
    m.positions[:, :, 2] += 0.04 * np.cos(frequency * t)[:, None]
    assert [e for e in detect_markers(m) if e.confidence >= 0.8] == []


def test_legitimate_zero_coordinates_are_valid():
    m = make_markers()
    m.positions[:, 0] = 0
    assert gaps(m) == []
