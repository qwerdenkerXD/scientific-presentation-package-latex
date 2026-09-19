#!/usr/bin/env python3
"""Check that thbtalk.sty still renders exactly like a reference version.

Compiles test/coverage.tex in every variant twice, once with the working-tree
thbtalk.sty and once with the reference, renders all pages with pdftocairo and
compares them pixel by pixel.

    python3 test/check.py              # reference = thbtalk.sty as committed in HEAD
    python3 test/check.py 553a06b      # reference = any git revision
    python3 test/check.py old.sty      # reference = a file

Exit code 0 means every page of every variant is identical. For each page that
differs, a diff image (changed pixels in red) is written to test/build/.
Needs pdflatex, pdftocairo (poppler-utils) and Pillow.
"""
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageChops

TEST_DIR = Path(__file__).resolve().parent
REPO_DIR = TEST_DIR.parent
BUILD_DIR = TEST_DIR / "build"
INPUT_FILES = ["coverage.tex", "logo.png", "photo.png"]
VARIANTS = ["default", "german", "bare", "notes"]
RENDER_DPI = 150
# pdflatex stays far below this; the cap only guards the WSL VM against runaways.
MEMORY_CAP = ["systemd-run", "--user", "--scope", "-q",
              "-p", "MemoryMax=1G", "-p", "MemorySwapMax=0"]


def write_reference_package(reference, target):
    """Write the reference thbtalk.sty (a file path or a git revision) to target."""
    reference_path = Path(reference)
    if reference_path.is_file():
        shutil.copyfile(reference_path, target)
        return
    committed = subprocess.run(["git", "show", f"{reference}:thbtalk.sty"], cwd=REPO_DIR,
                               capture_output=True, check=True)
    target.write_bytes(committed.stdout)


def compile_and_render(work_dir, variant):
    """Compile coverage.tex twice in work_dir and render its pages. Returns the page images."""
    command = MEMORY_CAP + ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                            rf"\def\variant{{{variant}}}\input{{coverage}}"]
    for _ in range(2):  # second run picks up the outline, navigation and page references
        run = subprocess.run(command, cwd=work_dir, capture_output=True)
        if run.returncode != 0:
            log_lines = (work_dir / "coverage.log").read_text(errors="replace").splitlines()
            first_error = next((i for i, line in enumerate(log_lines) if line.startswith("!")), None)
            excerpt = log_lines[first_error:first_error + 6] if first_error is not None else log_lines[-10:]
            raise RuntimeError(f"{work_dir}: pdflatex failed\n  " + "\n  ".join(excerpt))
    # pdftocairo, not pdftoppm: pdftoppm snaps rule edges to whole pixels and misses
    # sub-pixel changes; cairo renders edges with fractional coverage.
    subprocess.run(["pdftocairo", "-png", "-r", str(RENDER_DPI), "coverage.pdf", "page"],
                   cwd=work_dir, check=True)
    return sorted(work_dir.glob("page-*.png"))


def build(variant, side, package_source):
    work_dir = BUILD_DIR / variant / side
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True)
    for name in INPUT_FILES:
        shutil.copyfile(TEST_DIR / name, work_dir / name)
    package_source(work_dir / "thbtalk.sty")
    return compile_and_render(work_dir, variant)


def compare_variant(variant, reference):
    for stale_diff in (BUILD_DIR / variant).glob("diff-page-*.png"):
        stale_diff.unlink()
    reference_pages = build(variant, "reference",
                            lambda target: write_reference_package(reference, target))
    current_pages = build(variant, "current",
                          lambda target: shutil.copyfile(REPO_DIR / "thbtalk.sty", target))
    problems = []
    if len(reference_pages) != len(current_pages):
        problems.append(f"page count {len(reference_pages)} -> {len(current_pages)}")
    for page_number, (reference_page, current_page) in enumerate(
            zip(reference_pages, current_pages), start=1):
        with Image.open(reference_page) as old, Image.open(current_page) as new:
            if old.size != new.size:
                problems.append(f"page {page_number}: size {old.size} -> {new.size}")
                continue
            difference = ImageChops.difference(old.convert("RGB"), new.convert("RGB"))
            changed_area = difference.getbbox()
            if changed_area is None:
                continue
            problems.append(f"page {page_number}: pixels differ in box {changed_area}")
            changed_mask = difference.convert("L").point(lambda value: 255 if value else 0)
            highlighted = new.convert("RGB")
            highlighted.paste((255, 0, 0), mask=changed_mask)
            highlighted.save(BUILD_DIR / variant / f"diff-page-{page_number:02d}.png")
    return len(current_pages), problems


def main():
    reference = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    with ThreadPoolExecutor(max_workers=len(VARIANTS)) as pool:
        results = dict(zip(VARIANTS, pool.map(
            lambda variant: compare_variant(variant, reference), VARIANTS)))
    all_identical = True
    for variant, (page_count, problems) in results.items():
        verdict = "identical" if not problems else "DIFFERENT"
        print(f"{variant:8} {page_count:3} pages  {verdict}")
        for problem in problems:
            print(f"         {problem}")
        all_identical = all_identical and not problems
    return 0 if all_identical else 1


if __name__ == "__main__":
    sys.exit(main())
