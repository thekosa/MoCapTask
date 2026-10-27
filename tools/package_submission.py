"""Package a clean local repository, including .git, without its virtual environment."""

from pathlib import Path
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    if not (ROOT / ".git").is_dir():
        raise SystemExit("Expected a standalone repository with a .git directory.")
    if git("status", "--porcelain"):
        raise SystemExit(
            "Commit all deliverables before packaging; the worktree is not clean."
        )
    tracked = [
        ROOT / p.decode("utf-8") for p in git("ls-files", "-z").split(b"\0") if p
    ]
    history = [p for p in (ROOT / ".git").rglob("*") if p.is_file()]
    paths = sorted(set(tracked + history))
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise SystemExit(f"Refusing a linked/external archive entry: {path}")
        if path.name.endswith(".lock") and ".git" in path.relative_to(ROOT).parts:
            raise SystemExit(f"Git is busy (lock file present): {path}")
    output = ROOT / "submission.zip"
    temporary = ROOT / "submission.zip.tmp"
    try:
        with ZipFile(temporary, "w", ZIP_DEFLATED, compresslevel=6) as archive:
            for path in paths:
                archive.write(path, "mocap-qc/" + path.relative_to(ROOT).as_posix())
        with ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise SystemExit("ZIP integrity check failed.")
            for path in tracked:
                if (
                    archive.read("mocap-qc/" + path.relative_to(ROOT).as_posix())
                    != path.read_bytes()
                ):
                    raise SystemExit(f"Archived bytes differ: {path}")
            if "mocap-qc/.git/HEAD" not in archive.namelist():
                raise SystemExit("Git history missing from archive.")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(
        f"Created {output.name}: {len(tracked)} tracked files plus .git, {output.stat().st_size:,} bytes."
    )


if __name__ == "__main__":
    main()
