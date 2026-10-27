"""Exercise the real CLI on supplied data; these are regression checks, not ground truth."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_supplied_take_cli_and_input_preservation(tmp_path):
    inputs = [ROOT / "mocap/data/take.c3d", ROOT / "mocap/data/take.usd"]
    before = [digest(path) for path in inputs]
    result = subprocess.run(
        [sys.executable, "-m", "mocap_qc", *map(str, inputs), "-o", str(tmp_path)],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert [digest(path) for path in inputs] == before
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["skel_to_c3d_offset_frames"] == 18
    events = report["events"]
    assert events and all(0 <= e["start"] <= e["end"] < 3600 and .8 <= e["confidence"] <= 1 for e in events)
    assert any(e["type"] == "gap" and e["targets"] == ["A1:RTOE"]
               and (e["start"], e["end"]) == (2600, 2660) for e in events)
    assert any(e["type"] == "rotation_excursion" and (e["start"], e["end"]) == (1200, 1215)
               for e in events)
    assert (tmp_path / "report.md").is_file()
