#!/usr/bin/env python3
"""Build demo.pdf in the repository root from demo.tex and thbtalk.sty.

    python3 test/build_demo.py

Run it whenever demo.tex or thbtalk.sty change, and commit demo.pdf with them;
test/check.py reports a demo.pdf that no longer matches its sources. The build uses a
fixed date for \\today, so the PDF only changes when the sources do.
Needs pdflatex.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
REPO_DIR = TEST_DIR.parent
DEMO_BUILD_DIR = TEST_DIR / "build" / "demo"
DEMO_DATE = "1789776000"   # 2026-09-19, as seconds since 1970, for SOURCE_DATE_EPOCH
# pdflatex stays far below this; the cap only guards the WSL VM against runaways.
MEMORY_CAP = ["systemd-run", "--user", "--scope", "-q",
              "-p", "MemoryMax=1G", "-p", "MemorySwapMax=0"]


class CompileError(Exception):
    pass


def run_pdflatex(work_dir, job_name, tex_input, environment=None):
    """Compile twice (the second run picks up outline, navigation and page references).
    Raises CompileError with the first LaTeX error."""
    command = MEMORY_CAP + ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                            f"-jobname={job_name}", tex_input]
    for _ in range(2):
        run = subprocess.run(command, cwd=work_dir, capture_output=True,
                             env={**os.environ, **(environment or {})})
        if run.returncode != 0:
            log_lines = (work_dir / f"{job_name}.log").read_text(errors="replace").splitlines()
            first_error = next((i for i, line in enumerate(log_lines) if line.startswith("!")), None)
            excerpt = log_lines[first_error:first_error + 3] if first_error is not None else log_lines[-5:]
            raise CompileError("\n           ".join(excerpt))
    return work_dir / f"{job_name}.pdf"


def build_demo(work_dir=DEMO_BUILD_DIR):
    """Compile demo.tex with the working-tree package in work_dir; returns the PDF."""
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True)
    for name in ["demo.tex", "thbtalk.sty"]:
        shutil.copyfile(REPO_DIR / name, work_dir / name)
    return run_pdflatex(work_dir, "demo", "demo.tex",
                        {"SOURCE_DATE_EPOCH": DEMO_DATE, "FORCE_SOURCE_DATE": "1"})


def main():
    try:
        pdf = build_demo()
    except CompileError as error:
        sys.exit(f"demo.tex does not compile:\n           {error}")
    shutil.copyfile(pdf, REPO_DIR / "demo.pdf")
    print(f"demo.pdf written ({pdf.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
