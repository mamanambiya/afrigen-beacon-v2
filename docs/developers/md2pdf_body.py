"""Build the pandoc input body for md2pdf.sh.

Decides the document title, and whether the source's own H1 should be dropped
from the body.

The H1 used to be lifted into the title AND left in place, so it rendered
twice: once as the document title, again as numbered section 1.

Heading detection must ignore fenced code blocks. A plain `grep '^# '` counts a
shell comment such as `# GNU/Linux: sed ...` as an H1 — which is exactly what
it did on the beacon tutorial, making a one-H1 document look like a two-H1 one.
"""
import pathlib
import re
import sys

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)")

PREAMBLE = [
    "geometry: margin=2.5cm",
    "toc: true",
    "toc-depth: 3",
    "numbersections: true",
    "colorlinks: true",
    "header-includes:",
    r"  - \usepackage{fvextra}",
    r"  - \usepackage{xcolor}",
    r"  - \usepackage[htt]{hyphenat}",
    # NOT framemethod=TikZ: that method cannot split a shaded box across a
    # page boundary and fails with a cascade of "Overfull \\vbox" as it
    # retries — 204 of them on the beacon tutorial, against 0 here.
    r"  - \usepackage{mdframed}",
    r"  - \definecolor{codebg}{RGB}{246,246,246}",
    r"  - \DefineVerbatimEnvironment{verbatim}{Verbatim}"
    r"{breaklines,breakanywhere,fontsize=\small}",
    r"  - \surroundwithmdframed[backgroundcolor=codebg,linewidth=0pt,"
    r"innertopmargin=5pt,innerbottommargin=5pt,innerleftmargin=5pt,"
    r"innerrightmargin=5pt,skipabove=6pt,skipbelow=6pt]{verbatim}",
]


def headings(lines):
    """Every real Markdown heading, skipping anything inside a code fence."""
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING.match(line)
        if m:
            yield i, len(m.group(1)), m.group(2).strip()


def main(src_path, body_path, flag_path):
    src = pathlib.Path(src_path)
    lines = src.read_text().split("\n")
    found = list(headings(lines))
    h1s = [h for h in found if h[1] == 1]

    title, body, shift = src.stem, lines, "no"

    # Only drop the H1 when there is exactly one and it opens the document. A
    # file with several top-level sections has to keep all of them.
    if len(h1s) == 1 and found and found[0][1] == 1:
        index, _, text = h1s[0]
        title = text
        body = lines[:index] + lines[index + 1:]
        shift = "yes"
    elif h1s:
        title = h1s[0][2]

    yaml = ["---", 'title: "%s"' % title.replace('"', r'\"')] + PREAMBLE + ["---", ""]
    pathlib.Path(body_path).write_text("\n".join(yaml + body))
    pathlib.Path(flag_path).write_text(shift)


if __name__ == "__main__":
    main(*sys.argv[1:4])
