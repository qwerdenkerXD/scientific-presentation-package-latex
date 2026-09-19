#!/usr/bin/env python3
"""Compare thbtalk.sty with the design it follows (design/thbtalk-preview.html).

Renders the 13 design slides with Playwright (Chromium, fonts from Google Fonts), builds
test/design.tex (the same content) with the working-tree thbtalk.sty, and for every slide
- writes test/build/design/pair-NN.png (design left, LaTeX right) and blend-NN.png (both at 50 %),
- prints the ink bands (rows that differ from the background) of both, with the vertical offset.

    python3 test/design_check.py            # all slides
    python3 test/design_check.py 4 13       # only these slides

A band is a run of rows with ink; its left and right end show horizontal placement. An offset of
a few pixels is rendering noise; more means a size or spacing differs from the design.
Set THB_CHROMIUM to a Chromium executable if Playwright's own browser is not installed.
Needs pdflatex, pdftocairo (poppler-utils), Pillow, numpy and playwright.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TEST_DIR = Path(__file__).resolve().parent
REPO_DIR = TEST_DIR.parent
DESIGN_HTML = REPO_DIR / "design" / "thbtalk-preview.html"
BUILD_DIR = TEST_DIR / "build" / "design"
WIDTH, HEIGHT = 1920, 1080
# design slide -> page of design.pdf (the design deck has no divider slides for Method and Results)
DESIGN_TO_PAGE = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 7, 7: 8, 8: 9, 9: 11, 10: 12, 11: 13, 12: 14, 13: 15}
MEMORY_CAP = ["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=1G", "-p", "MemorySwapMax=0"]


def render_design():
    """Render each <section> of the design as deck-stage shows it: 1920x1080, border-box, clipped."""
    from playwright.sync_api import sync_playwright
    html = DESIGN_HTML.read_text(encoding="utf-8")
    head = re.search(r"<helmet>(.*?)</helmet>", html, re.S).group(1)
    sections = re.findall(r"<section\b.*?</section>", html, re.S)
    slide_css = ("<style>section{position:absolute!important;inset:0!important;width:1920px!important;"
                 "height:1080px!important;box-sizing:border-box!important;overflow:hidden}</style>")
    with sync_playwright() as playwright:
        chromium = os.environ.get("THB_CHROMIUM")
        browser = playwright.chromium.launch(**({"executable_path": chromium} if chromium else {}))
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        for number, section in enumerate(sections, start=1):
            page.set_content(f"<!DOCTYPE html><html><head><meta charset='utf-8'>{head}{slide_css}</head>"
                             f"<body style='margin:0'>{section}</body></html>", wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(BUILD_DIR / f"design-{number:02d}.png"))
        browser.close()


def build_latex():
    """Compile design.tex with the working-tree package; return the rendered pages."""
    for name in ["design.tex", "stripes.png"]:
        shutil.copyfile(TEST_DIR / name, BUILD_DIR / name)
    shutil.copyfile(REPO_DIR / "thbtalk.sty", BUILD_DIR / "thbtalk.sty")
    for _ in range(2):
        run = subprocess.run(MEMORY_CAP + ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "design"],
                             cwd=BUILD_DIR, capture_output=True)
        if run.returncode:
            sys.exit((BUILD_DIR / "design.log").read_text(errors="replace")[-2500:])
    for old_page in BUILD_DIR.glob("latex-*.png"):
        old_page.unlink()
    subprocess.run(["pdftocairo", "-png", "-scale-to-x", str(WIDTH), "-scale-to-y", str(HEIGHT),
                    "design.pdf", "latex"], cwd=BUILD_DIR, check=True)
    return sorted(BUILD_DIR.glob("latex-*.png"))


def ink_bands(image):
    """(top, bottom, left, right) of every run of rows that differ from the background colour."""
    pixels = np.asarray(image).astype(int)
    background = pixels[5, 5]
    ink = np.abs(pixels - background).sum(axis=2) > 60
    rows = ink.any(axis=1)
    bands, y = [], 0
    while y < len(rows):
        if rows[y]:
            top = y
            while y < len(rows) and rows[y:y + 3].any():   # gaps under 3 px stay in the band
                y += 1
            columns = np.nonzero(ink[top:y].any(axis=0))[0]
            bands.append((top, y - 1, columns.min(), columns.max()))
        y += 1
    return bands


def compare(slide, latex_page):
    design = Image.open(BUILD_DIR / f"design-{slide:02d}.png").convert("RGB")
    latex = Image.open(latex_page).convert("RGB")
    Image.blend(design, latex, 0.5).save(BUILD_DIR / f"blend-{slide:02d}.png")
    pair = Image.new("RGB", (2 * WIDTH + 20, HEIGHT), "gray")
    pair.paste(design, (0, 0))
    pair.paste(latex, (WIDTH + 20, 0))
    pair.save(BUILD_DIR / f"pair-{slide:02d}.png")
    print(f"== slide {slide}    design top-bottom left-right | latex top-bottom left-right | offset")
    design_bands, latex_bands = ink_bands(design), ink_bands(latex)
    for index in range(max(len(design_bands), len(latex_bands))):
        cells = []
        for bands in (design_bands, latex_bands):
            band = bands[index] if index < len(bands) else None
            cells.append(f"{band[0]:5}-{band[1]:<5}{band[2]:5}-{band[3]:<5}" if band else " " * 22)
        both = index < len(design_bands) and index < len(latex_bands)
        offset = latex_bands[index][0] - design_bands[index][0] if both else ""
        print(f"{'':12}{cells[0]:>26} | {cells[1]:>26} | {offset}")


def main():
    slides = [int(argument) for argument in sys.argv[1:]] or list(DESIGN_TO_PAGE)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    render_design()
    latex_pages = build_latex()
    for slide in slides:
        compare(slide, latex_pages[DESIGN_TO_PAGE[slide] - 1])


if __name__ == "__main__":
    main()
