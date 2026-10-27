import pytest

from mocap_qc import pipeline
from mocap_qc.models import Event
from conftest import make_markers, make_skeleton


def stub_inputs(monkeypatch):
    m, s = make_markers(), make_skeleton()
    monkeypatch.setattr(pipeline, "read_c3d", lambda path: m)
    monkeypatch.setattr(pipeline, "read_usd", lambda path: s)
    monkeypatch.setattr(pipeline, "detect_skeleton", lambda take: [])
    return m, s


def test_threshold_is_inclusive_and_events_are_sorted(monkeypatch):
    stub_inputs(monkeypatch)
    events = [
        Event("test", ("A1:P0",), 80, 80, .8, "at threshold"),
        Event("test", ("A1:P1",), 10, 10, .9, "earlier"),
        Event("test", ("A1:P2",), 20, 20, .799, "below"),
    ]
    monkeypatch.setattr(pipeline, "detect_markers", lambda take: events)
    result = pipeline.analyze("a", "b", offset_frames=18, min_confidence=.8)
    assert [e.start for e in result.events] == [10, 80]
    assert result.candidate_count == 3
    assert result.alignment.offset == 18


def test_manual_offset_without_overlap_is_rejected(monkeypatch):
    stub_inputs(monkeypatch)
    with pytest.raises(ValueError, match="no overlap"):
        pipeline.analyze("a", "b", offset_frames=10000)
