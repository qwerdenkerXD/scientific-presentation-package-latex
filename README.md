# thbtalk — a reusable beamer theme for scientific talks

pdfLaTeX, 16:9, one `.sty` file. Drop `thbtalk.sty` next to your `.tex` file (or into
`~/texmf/tex/latex/thbtalk/`) and compile `demo.tex` twice.

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
| `font=lmodern` \| `helvet` \| `none` | text font; default `lmodern` |
| `nodots` | hide the section navigation dots in the header |
| `nofooter` | hide the footer line |
| `nonumbers` | hide slide numbers |
| `nosectionslides` | do not auto-insert a divider slide at each `\section` |
| `notes=none\|second\|only` | speaker notes: off, second screen, or notes-only PDF |

Switch language mid-document with `\thbsetlang{de}`.

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
- `\thbbackup` — divider for backup slides; everything after it is excluded from the slide count

## Content helpers

```latex
\begin{takeaway}          One-sentence message of the slide.  \end{takeaway}
\begin{takeaway}[Fazit]   Custom heading.                     \end{takeaway}

\begin{twocols}           % optional width arg: \begin{twocols}[0.55]
  left column
  \colbreak
  right column
\end{twocols}

\thbfigure[0.7]{plot.pdf}{Caption below the figure.}
\thbplaceholder[0.7]{4cm}{sensor map}     % grey stand-in until the figure exists

\begin{pseudocode}{Greedy scheduler}      % algpseudocode inside a block
  \State $S \gets \emptyset$
\end{pseudocode}

\begin{code}[language=Python] ... \end{code}   % frame must be [fragile]

\begin{keyeq}\begin{equation} ... \end{equation}\end{keyeq}   % equation on a tinted band

\thbnumber{39\,\%}{lower error at the same energy budget}      % one headline result
\thbquote{Statement.}{Author, Year}                            % cited statement
\thbfullfigure{photo.jpg}{Caption strip along the bottom.}     % full-bleed image slide
```

Equations, theorems and code are deliberately styled differently so the audience can tell
them apart at a glance: equations sit on a tinted band, theorems carry a green left rule,
code a blue one. Blocks and `takeaway` keep the filled header bar.

Tables: `booktabs` is loaded; use `\thbhead{Column}` for header cells.
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

`beamer`, `kvoptions`, `xcolor`, `graphicx`, `booktabs`, `listings`, `amsmath`,
`tikz`, `pgfplots`, `algpseudocode` — all in a standard TeX Live / MiKTeX / Overleaf
installation.
