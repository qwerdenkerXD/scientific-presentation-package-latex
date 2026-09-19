#!/usr/bin/env python3
"""Check that thbtalk.sty still renders exactly like a reference version.

Compiles the reference's test/coverage.tex in every variant twice, once with the reference
thbtalk.sty and once with the working-tree one, renders all pages with pdftocairo and
compares them pixel by pixel. So the comparison covers everything both versions have.
If the working-tree coverage.tex differs (a new command was added to it), it is compiled
with the working-tree package as well: new commands have no reference to look like, but
they must compile.

    python3 test/check.py              # reference = HEAD
    python3 test/check.py 553a06b      # reference = any git revision
    python3 test/check.py old.sty      # reference = a file (tested with the working-tree coverage.tex)

A revision without test files uses the working-tree ones. Finally it rebuilds the demo and
checks that the committed demo.pdf still matches demo.tex and thbtalk.sty (if not, run
python3 test/build_demo.py). Exit code 0 means every page of every variant is identical,
everything compiles and demo.pdf is current. For each page that differs, a diff image
(changed pixels in red) is written to test/build/<variant>/ or test/build/demo-check/.
Needs pdflatex, pdftocairo (poppler-utils) and Pillow.
"""
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageChops

from build_demo import CompileError, build_demo, run_pdflatex

TEST_DIR = Path(__file__).resolve().parent
REPO_DIR = TEST_DIR.parent
BUILD_DIR = TEST_DIR / "build"
TEST_FILES = ["coverage.tex", "logo.png", "photo.png"]
VARIANTS = ["default", "german", "bare", "notes"]
RENDER_DPI = 150


def committed_file(revision, path):
    """The file's content at a git revision, or None if it did not exist there."""
    shown = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=REPO_DIR, capture_output=True)
    return shown.stdout if shown.returncode == 0 else None


def working_tree_inputs():
    """Package and test files as they are in the working tree."""
    return {"thbtalk.sty": (REPO_DIR / "thbtalk.sty").read_bytes(),
            **{name: (TEST_DIR / name).read_bytes() for name in TEST_FILES}}


def reference_inputs(reference):
    """Package and test files of the reference (a .sty file or a git revision), and where
    the test files come from."""
    current = working_tree_inputs()
    if Path(reference).is_file():
        return {**current, "thbtalk.sty": Path(reference).read_bytes()}, "the working tree's"
    package = committed_file(reference, "thbtalk.sty")
    if package is None:
        sys.exit(f"{reference}: no thbtalk.sty at this revision")
    test_files = {name: committed_file(reference, f"test/{name}") for name in TEST_FILES}
    if None in test_files.values():   # a revision from before the tests existed
        return {"thbtalk.sty": package, **{name: current[name] for name in TEST_FILES}}, \
            "the working tree's (the revision has none)"
    return {"thbtalk.sty": package, **test_files}, f"{reference}'s"


def render_pages(pdf, output_dir, prefix):
    """Render every page of pdf to <output_dir>/<prefix>-NN.png; returns them in order."""
    for old_page in output_dir.glob(f"{prefix}-*.png"):
        old_page.unlink()
    # pdftocairo, not pdftoppm: pdftoppm snaps rule edges to whole pixels and misses
    # sub-pixel changes; cairo renders edges with fractional coverage.
    subprocess.run(["pdftocairo", "-png", "-r", str(RENDER_DPI), str(pdf), prefix],
                   cwd=output_dir, check=True)
    return sorted(output_dir.glob(f"{prefix}-*.png"))


def compile_and_render(work_dir, variant, render):
    """Compile coverage.tex in work_dir; with render, return its pages as images."""
    pdf = run_pdflatex(work_dir, "coverage", rf"\def\variant{{{variant}}}\input{{coverage}}")
    return render_pages(pdf, work_dir, "page") if render else []


def build(variant, side, files, render=True):
    """Write files into test/build/<variant>/<side>/ and compile there."""
    work_dir = BUILD_DIR / variant / side
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True)
    for name, content in files.items():
        (work_dir / name).write_bytes(content)
    return compile_and_render(work_dir, variant, render)


def compare_pages(diff_dir, reference_pages, current_pages):
    """Problems found comparing two lists of page images; marks changed pixels in diff_dir."""
    for stale_diff in diff_dir.glob("diff-page-*.png"):
        stale_diff.unlink()
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
            highlighted.save(diff_dir / f"diff-page-{page_number:02d}.png")
    return problems


def check_variant(variant, reference_files, tests_source, current_files):
    """Returns (page count, list of problems) for one variant."""
    (BUILD_DIR / variant).mkdir(parents=True, exist_ok=True)
    test_files = {name: reference_files[name] for name in TEST_FILES}
    try:
        reference_pages = build(variant, "reference", reference_files)
    except CompileError as error:
        return 0, [f"the reference package does not compile {tests_source} coverage.tex:\n           {error}"]
    try:
        current_pages = build(variant, "current", {**test_files, "thbtalk.sty": current_files["thbtalk.sty"]})
    except CompileError as error:
        return 0, [f"the working-tree package does not compile {tests_source} coverage.tex:\n           {error}"]
    problems = compare_pages(BUILD_DIR / variant, reference_pages, current_pages)
    if any(current_files[name] != test_files[name] for name in TEST_FILES):
        try:
            build(variant, "current-new-tests", current_files, render=False)
        except CompileError as error:
            problems.append(f"the working-tree coverage.tex does not compile:\n           {error}")
    return len(current_pages), problems


def check_demo():
    """Problems of the committed demo.pdf: it must match a fresh build of its sources."""
    check_dir = BUILD_DIR / "demo-check"
    try:
        fresh_pdf = build_demo(check_dir)
    except CompileError as error:
        return [f"demo.tex does not compile:\n           {error}"]
    committed_pdf = REPO_DIR / "demo.pdf"
    if not committed_pdf.exists():
        return ["there is no demo.pdf"]
    problems = compare_pages(check_dir, render_pages(committed_pdf, check_dir, "committed"),
                             render_pages(fresh_pdf, check_dir, "fresh"))
    return problems and problems + ["demo.pdf is out of date: run python3 test/build_demo.py"]


def main():
    reference = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    reference_files, tests_source = reference_inputs(reference)
    current_files = working_tree_inputs()
    tests_changed = any(current_files[name] != reference_files[name] for name in TEST_FILES)
    with ThreadPoolExecutor(max_workers=len(VARIANTS) + 1) as pool:
        demo_check = pool.submit(check_demo)
        results = dict(zip(VARIANTS, pool.map(
            lambda variant: check_variant(variant, reference_files, tests_source, current_files), VARIANTS)))
        demo_problems = demo_check.result()
    all_good = True
    for variant, (page_count, problems) in results.items():
        verdict = "identical" if not problems else "NOT OK"
        print(f"{variant:8} {page_count:3} pages  {verdict}")
        for problem in problems:
            print(f"         {problem}")
        all_good = all_good and not problems
    if tests_changed:
        print("The working-tree test files differ from the reference's: compared on the reference's,"
              "\nand the new ones compiled with the working-tree package"
              + (" without errors." if all_good else "."))
    print("demo.pdf matches demo.tex and thbtalk.sty" if not demo_problems else "demo.pdf NOT OK")
    for problem in demo_problems:
        print(f"         {problem}")
    return 0 if all_good and not demo_problems else 1


if __name__ == "__main__":
    sys.exit(main())
