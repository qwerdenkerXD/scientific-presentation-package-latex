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

A revision without test files uses the working-tree ones. Exit code 0 means every page of
every variant is identical and everything compiles. For each page that differs, a diff
image (changed pixels in red) is written to test/build/<variant>/.
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
TEST_FILES = ["coverage.tex", "logo.png", "photo.png"]
VARIANTS = ["default", "german", "bare", "notes"]
RENDER_DPI = 150
# pdflatex stays far below this; the cap only guards the WSL VM against runaways.
MEMORY_CAP = ["systemd-run", "--user", "--scope", "-q",
              "-p", "MemoryMax=1G", "-p", "MemorySwapMax=0"]


class CompileError(Exception):
    pass


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


def compile_and_render(work_dir, variant, render):
    """Compile coverage.tex twice in work_dir; with render, return its pages as images."""
    command = MEMORY_CAP + ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                            rf"\def\variant{{{variant}}}\input{{coverage}}"]
    for _ in range(2):  # second run picks up the outline, navigation and page references
        run = subprocess.run(command, cwd=work_dir, capture_output=True)
        if run.returncode != 0:
            log_lines = (work_dir / "coverage.log").read_text(errors="replace").splitlines()
            first_error = next((i for i, line in enumerate(log_lines) if line.startswith("!")), None)
            excerpt = log_lines[first_error:first_error + 3] if first_error is not None else log_lines[-5:]
            raise CompileError("\n           ".join(excerpt))
    if not render:
        return []
    # pdftocairo, not pdftoppm: pdftoppm snaps rule edges to whole pixels and misses
    # sub-pixel changes; cairo renders edges with fractional coverage.
    subprocess.run(["pdftocairo", "-png", "-r", str(RENDER_DPI), "coverage.pdf", "page"],
                   cwd=work_dir, check=True)
    return sorted(work_dir.glob("page-*.png"))


def build(variant, side, files, render=True):
    """Write files into test/build/<variant>/<side>/ and compile there."""
    work_dir = BUILD_DIR / variant / side
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True)
    for name, content in files.items():
        (work_dir / name).write_bytes(content)
    return compile_and_render(work_dir, variant, render)


def compare_pages(variant, reference_pages, current_pages):
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
    return problems


def check_variant(variant, reference_files, tests_source, current_files):
    """Returns (page count, list of problems) for one variant."""
    (BUILD_DIR / variant).mkdir(parents=True, exist_ok=True)
    for stale_diff in (BUILD_DIR / variant).glob("diff-page-*.png"):
        stale_diff.unlink()
    test_files = {name: reference_files[name] for name in TEST_FILES}
    try:
        reference_pages = build(variant, "reference", reference_files)
    except CompileError as error:
        return 0, [f"the reference package does not compile {tests_source} coverage.tex:\n           {error}"]
    try:
        current_pages = build(variant, "current", {**test_files, "thbtalk.sty": current_files["thbtalk.sty"]})
    except CompileError as error:
        return 0, [f"the working-tree package does not compile {tests_source} coverage.tex:\n           {error}"]
    problems = compare_pages(variant, reference_pages, current_pages)
    if any(current_files[name] != test_files[name] for name in TEST_FILES):
        try:
            build(variant, "current-new-tests", current_files, render=False)
        except CompileError as error:
            problems.append(f"the working-tree coverage.tex does not compile:\n           {error}")
    return len(current_pages), problems


def main():
    reference = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    reference_files, tests_source = reference_inputs(reference)
    current_files = working_tree_inputs()
    tests_changed = any(current_files[name] != reference_files[name] for name in TEST_FILES)
    with ThreadPoolExecutor(max_workers=len(VARIANTS)) as pool:
        results = dict(zip(VARIANTS, pool.map(
            lambda variant: check_variant(variant, reference_files, tests_source, current_files), VARIANTS)))
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
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
