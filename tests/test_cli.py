import pytest

from mocap_qc import cli
from mocap_qc.models import Alignment, Event
from mocap_qc.pipeline import Analysis
from conftest import make_markers, make_skeleton


@pytest.mark.parametrize(
    "flags, expected",
    [
        ([], 0.80),
        (["--review-low-confidence"], 0.70),
        (["--min-confidence", "0.70"], 0.70),
        (["--min-confidence", "0.90"], 0.90),
        (["--min-confidence", "0"], 0.0),
    ],
)
def test_cli_passes_selected_cutoff_and_reports_it(
    tmp_path, monkeypatch, flags, expected
):
    c3d, usd = tmp_path / "input.c3d", tmp_path / "input.usd"
    c3d.touch()
    usd.touch()
    out = tmp_path / "out"
    received = []
    candidates = [
        Event("marker_discontinuity", ("A1:P0",), 10, 10, 0.70, "Review candidate."),
        Event("spike", ("A1:P1",), 20, 20, 0.90, "Short excursion."),
    ]

    def analyze(*args, min_confidence, **kwargs):
        received.append(min_confidence)
        return Analysis(
            make_markers(),
            make_skeleton(),
            Alignment(18, "test", 0.9),
            [event for event in candidates if event.confidence >= min_confidence],
            min_confidence,
            len(candidates),
        )

    monkeypatch.setattr(cli, "analyze", analyze)
    assert cli.main([str(c3d), str(usd), "-o", str(out), *flags]) == 0
    assert received == [expected]
    text = (out / "report.md").read_text(encoding="utf-8")
    assert f"confidence >= {expected * 100:g}%" in text
    assert "heuristic evidence score" in text
    assert "not a calibrated probability" in text


@pytest.mark.parametrize(
    "flags",
    [
        ["--review-low-confidence", "--min-confidence", "0.70"],
        ["--min-confidence", "0.90", "--review-low-confidence"],
    ],
)
def test_review_and_numeric_cutoffs_are_mutually_exclusive(tmp_path, capsys, flags):
    out = tmp_path / "out"
    with pytest.raises(SystemExit) as error:
        cli.main(["missing.c3d", "missing.usd", "-o", str(out), *flags])
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "not allowed with argument" in message
    assert "--review-low-confidence" in message
    assert "--min-confidence" in message
    assert not out.exists()
