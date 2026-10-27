import json

import pytest

from mocap_qc.cli import main
from mocap_qc.models import Alignment, Event
from mocap_qc.pipeline import Analysis
from mocap_qc.reporting import write_reports, validate_output
from conftest import make_markers, make_skeleton


def test_exact_schema_and_human_threshold(tmp_path):
    analysis = Analysis(
        make_markers(),
        make_skeleton(),
        Alignment(18, "test", 0.9),
        [Event("spike", ("A1:P0",), 120, 121, 0.88, "24 mm excursion.")],
        0.8,
        3,
    )
    write_reports(analysis, tmp_path)
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert set(data) == {"skel_to_c3d_offset_frames", "events"}
    assert data["skel_to_c3d_offset_frames"] == 18
    assert set(data["events"][0]) == {
        "type",
        "targets",
        "start",
        "end",
        "confidence",
        "note",
    }
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "confidence >= 80%" in text
    assert "2 lower-score candidates omitted" in text
    assert "not a calibrated probability" in text
    assert "Suggested review" in text
    assert "## 1. spike \u2014 frames 120\u2013121" in text
    assert "1.000\u20131.008 s" in text
    assert "\u00e2\u20ac" not in text
    before = (tmp_path / "report.json").read_bytes()
    write_reports(analysis, tmp_path)
    assert (tmp_path / "report.json").read_bytes() == before
    assert not list(tmp_path.glob(".qc-*.tmp"))


@pytest.mark.parametrize("value", ["nan", "inf", "-0.01", "1.01"])
def test_invalid_confidence_rejected_before_reading(value):
    with pytest.raises(SystemExit) as error:
        main(["missing.c3d", "missing.usd", "-o", "unused", "--min-confidence", value])
    assert error.value.code == 2


def test_missing_input_no_output(tmp_path, capsys):
    out = tmp_path / "out"
    assert main(["missing.c3d", "missing.usd", "-o", str(out)]) == 2
    assert not out.exists()
    assert "does not exist" in capsys.readouterr().err


def test_output_cannot_overwrite_input(tmp_path):
    source = tmp_path / "report.json"
    source.write_bytes(b"original input")
    with pytest.raises(ValueError, match="overwrite"):
        validate_output(tmp_path, (source,))
    assert source.read_bytes() == b"original input"
