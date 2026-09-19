# thbtalk — a reusable beamer theme for scientific talks

pdfLaTeX, 16:9, one `.sty` file. Drop `thbtalk.sty` next to your `.tex` file (or into
`~/texmf/tex/latex/thbtalk/`) and compile `demo.tex` twice.

**See it first:** [`demo.pdf`](demo.pdf) is the demo talk, built from `demo.tex`.

The look follows the design in `design/thbtalk-preview.html` (open it in a browser). The
package sets its own type scale from that design: body text is 8 pt, whatever size option
you give `\documentclass`, and `\small`, `\large` etc. follow the design's steps.

## Minimal preamble

```latex
\documentclass[aspectratio=169,10pt]{beamer}
\usepackage[utf8]{inputenc}
\usepackage[english]{babel}
\usepackage{thbtalk}

\title{...}\subtitle{...}\author{...}\institute{...}\date{\today}
\thbvenue{Conference, City}
\thblogotext{TH Bingen}        % or \thblogo{logo.pdf} for an image

\begin{document}
\thbtitleframe
\thboutline
\section{Motivation}
\begin{frame}{Title}{Optional subtitle} ... \end{frame}
\thbclosingframe
\end{document}
```

## Package options

| Option | Effect |
|---|---|
| `lang=en` \| `lang=de` | built-in labels (Outline/Gliederung, Backup/Anhang, …) |
| `font=source` \| `lmodern` \| `helvet` \| `none` | default `source`: the design's fonts — Source Sans for text, Source Serif for quotes and maths, Source Code for code. `none` leaves fonts to you; they must scale to any size (e.g. `lmodern`) |
| `nodots` | hide the section navigation dots in the header |
| `nofooter` | hide the footer line |
| `nonumbers` | hide slide numbers |
| `nosectionslides` | do not auto-insert a divider slide at each `\section` |
| `notes=none\|second\|only` | speaker notes: off, second screen, or notes-only PDF |

A misspelt value (`font=helvtica`) stops with an error instead of silently using the default.

Switch language mid-document with `\thbsetlang{de}`. Add a language in the preamble; labels
you leave out keep their English text:

```latex
\thbdeclarelang{fr}{outline=Plan, questions=Questions~?, recap=À retenir}
\thbsetlang{fr}
```

The labels are `outline`, `takeaway`, `refs`, `backup`, `thanks`, `questions`, `figure`,
`recap` and `where`. `\thblabel{<label>}` prints one in the current language, so your own
slides switch language with the package's:

```latex
\begin{frame}{\thblabel{refs}} ... \end{frame}         % References / Literatur
\thbclosingframe[\thblabel{thanks}]                    % Thank you / Vielen Dank
\thblabel{figure}~1: Deployment area                    % Fig. 1 / Abb. 1
```

## Structure commands

- `\thbtitleframe` — title slide, logo top right (only there)
- `\thboutline` — numbered agenda; add a one-line gloss per section with
  `\thboutlinenote{1}{Where static sampling breaks down}` in the preamble.
  Subsections appear indented beneath their section.
  `\thboutline[4]` splits into two columns after section 4 — use it above ~5 sections.
  `\thboutlinecompact` (also takes the split argument) drops glosses, subsections and
  rules, for talks with many short sections.
- `\section{…}` — automatically inserts a full-colour divider slide
- `\thbagenda` — standalone progress slide, usable anywhere mid-talk
- `\thbclosingframe` — plain closing slide; optional argument overrides the text
- `closing` environment — closing slide with the recap kept on screen for Q&A:
  `\begin{closing}[Questions?] \item … \end{closing}`; set the contact line once with
  `\thbcontact{mail · DOI}`
- `\thbbackup` — divider slide before the backup slides; they are compiled and numbered as usual

Every slide is numbered, the title and divider slides included, so the number in the footer
is the page of the PDF (overlays aside).

## Content helpers

```latex
\begin{takeaway}          One-sentence message of the slide.  \end{takeaway}
\begin{takeaway}[Fazit]   Custom heading.                     \end{takeaway}

\begin{twocols}           % optional width arg: \begin{twocols}[0.55]
  left column
  \colbreak               % only valid inside twocols
  right column
\end{twocols}

\thbfigure[0.7]{plot.pdf}{Caption below the figure.}
\thbplaceholder[0.7]{4cm}{sensor map}     % grey stand-in until the figure exists

\begin{pseudocode}{Greedy scheduler}      % algpseudocode inside a block
  \State $S \gets \emptyset$
\end{pseudocode}

\begin{code}[language=Python] ... \end{code}   % frame must be [fragile]

\begin{keyeq}\begin{equation} ... \end{equation}\end{keyeq}   % equation on a tinted band

\thbnumber{39\,\%}{lower error at the same energy budget}      % one headline result, centred in the slide
\thbquote{Statement.}{Author, Year}                            % cited statement
\thbfullfigure{photo.jpg}{Caption strip along the bottom.}     % full-bleed image slide
\thbcmd{thbbackup}          % typesets \thbbackup; unlike \verb, no [fragile] needed
```

Equations, theorems and code are deliberately styled differently so the audience can tell
them apart at a glance: equations sit on a tinted band, theorems carry a green left rule,
code a blue one. Blocks and `takeaway` keep the filled header bar.

Some boxes are capped at the design's widths: `takeaway` 1150 px, theorems and `pseudocode`
1250 px, `code` 1350 px, `\thbquote` 1400 px (the design is 1920 px wide; the text 1708 px).
Tables: `booktabs` is loaded; use `\thbhead{Column}` for header cells. Every `tabular` gets
the design's airy rows and 28 px cell padding.
Plots: `pgfplots` is loaded; add `thbplot` to the axis options for the house style.
Theorems: `theorem`, `lemma`, `definition`, `proof` are numbered and use the palette.

## Bibliography

Works with either approach. Plain `thebibliography` needs nothing (see `demo.tex`).
For `biblatex` under pdfLaTeX:

```latex
\usepackage[style=numeric,backend=biber]{biblatex}
\addbibresource{refs.bib}
...
\begin{frame}[allowframebreaks]{References}\printbibliography\end{frame}
```

## Re-branding

Two lines, anywhere after `\usepackage{thbtalk}`:

```latex
\definecolor{thbprimary}{HTML}{004E9E}
\definecolor{thbaccent}{HTML}{78B833}
```

The defaults approximate the TH Bingen house colours — replace the hex values with
the exact ones from the corporate design sheet if they differ. Supporting neutrals
(`thbink`, `thbmuted`, `thbline`, `thbtint`, `thbcodebg`) can be overridden the same way.

## Required packages

LaTeX 2020-10 or newer, `beamer`, `kvoptions`, `etoolbox`, `ifthen`, `xcolor`, `graphicx`,
`booktabs`, `array`, `listings`, `amsmath`, `amssymb`, `tikz`, `pgfplots`, `algpseudocode`,
`tcolorbox`, and for the fonts `lmodern`, `sourcesanspro`, `sourceserifpro`, `sourcecodepro`,
`mathastext` — all in a standard TeX Live / MiKTeX / Overleaf installation.

## Changing the package

`demo.pdf` is committed so the demo can be seen without compiling. Whenever `demo.tex` or
`thbtalk.sty` change, rebuild it and commit it with them:

```sh
python3 test/build_demo.py       # writes demo.pdf (with a fixed date, so it only changes with its sources)
```

`test/coverage.tex` uses every command and option. After editing `thbtalk.sty`, run

```sh
python3 test/check.py            # compare against thbtalk.sty in HEAD (or: a revision, a file)
```

It compiles the coverage document in four variants with both versions, renders every page and
compares them pixel by pixel. It uses the reference's own `coverage.tex`, so the comparison
covers everything both versions have; if you added a command to `test/coverage.tex`, the new
version is compiled as well, since a new command has nothing to look like yet but must compile.
It also rebuilds the demo and reports a `demo.pdf` that no longer matches its sources.
Exit code 0 means nothing looks different, everything compiles and `demo.pdf` is current;
otherwise the problems are listed, and differing pages are marked red in
`test/build/<variant>/diff-page-NN.png` (or `test/build/demo-check/` for the demo). Needs `pdflatex`,
`pdftocairo` (poppler-utils) and Python with Pillow. When you add a command, add it to
`test/coverage.tex` as well.

To check the package against the design:

```sh
python3 test/design_check.py     # all 13 design slides; or: python3 test/design_check.py 4 13
```

It renders the design with Playwright, builds `test/design.tex` (the same content) and writes
side-by-side and 50 % blend images to `test/build/design/`. For each slide it prints the rows
with ink in both versions and their vertical offset, so a drift shows up as a number. All sizes
in `thbtalk.sty` are written in design pixels (`\thb@px`), so they can be read against the
HTML directly. Set `THB_CHROMIUM` to a Chromium executable if Playwright's own browser is
not installed.
