"""Command-line entry point; errors never silently become an empty/zero-offset report."""
import argparse
import math
from pathlib import Path
import sys

from .pipeline import analyze
from .reporting import validate_output, write_reports


def confidence(value):
    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("confidence must be a number from 0 to 1") from exc
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise argparse.ArgumentTypeError("confidence must be a finite number from 0 to 1")
    return result


def parser():
    result = argparse.ArgumentParser(
        description="Report motion-capture defects in C3D markers and a related UsdSkel animation. Inputs are read-only.")
    result.add_argument("c3d", type=Path, help="C3D marker file")
    result.add_argument("usd", type=Path, help="USD skeleton file")
    result.add_argument("-o", "--output", required=True, type=Path, help="directory for report.json and report.md")
    result.add_argument("--min-confidence", type=confidence, default=.80,
                        help="minimum heuristic evidence score, inclusive (default: 0.80; not a probability)")
    result.add_argument("--max-offset-frames", type=int, default=120,
                        help="automatic search radius in C3D frames (default: 120)")
    result.add_argument("--offset-frames", type=int,
                        help="verified C3D frame corresponding to the first USD pose; bypasses automatic timing")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        for path in (args.c3d, args.usd):
            if not path.is_file():
                raise ValueError(f"Input file does not exist: {path}")
        if args.c3d.resolve() == args.usd.resolve():
            raise ValueError("C3D and USD must be separate input files.")
        output = validate_output(args.output, (args.c3d, args.usd))
        analysis = analyze(args.c3d, args.usd, min_confidence=args.min_confidence,
                           offset_frames=args.offset_frames, max_offset_frames=args.max_offset_frames)
        write_reports(analysis, output, (args.c3d, args.usd))
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        print(f"mocap-qc: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {len(analysis.events)} events (confidence >= {analysis.min_confidence*100:.12g}%); "
          f"USD-to-C3D offset {analysis.alignment.offset:+d} frames. Reports: {output}")
    return 0
