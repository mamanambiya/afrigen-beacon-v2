#!/usr/bin/env bash
# Render a single Markdown file to standalone LaTeX, PDF and Word.
#
#   ./md2pdf.sh <input.md> [output-dir]
#
# Outputs <name>.tex, <name>.pdf and <name>.docx, defaulting to the input's own
# directory. The docx path does not go through LaTeX, so none of the font or
# line-breaking constraints below apply to it.
#
# Every option here is a defect this pipeline hit and fixed:
#
#   --from=markdown   NOT gfm. The gfm reader ignores the relative dash widths
#                     in a table's separator row, so wide tables render as
#                     non-wrapping columns and run off the page edge.
#   mainfont/monofont Latin Modern, the LaTeX default, contains NO Greek and no
#                     mathematical operators. pandoc still exits 0 and produces
#                     a PDF with holes in the equations, so the build greps the
#                     log and fails instead.
#   fvextra           LaTeX verbatim does not wrap. Any code line over ~78
#                     columns silently runs off the page, clipped mid-token.
#   --no-highlight    Highlighting wraps every token in a command group and
#                     fvextra cannot break inside one here (breaknonspaceingroup
#                     is undefined on this TeX distribution). Measured on the
#                     beacon tutorial: 15 clipped lines with highlighting, 7
#                     with a smaller code font, 1 without. A tutorial's value is
#                     commands you can paste, so completeness beats colour.
#   mdframed          --no-highlight also drops pandoc's shaded box, so code
#                     stops looking distinct from prose. This puts the light
#                     background back and, unlike a colorbox, breaks across
#                     pages.
#   hyphenat[htt]     Inline code does not break at all by default, so a long
#                     path in running prose overshoots the margin.

# TOOLCHAIN. Generated artefacts change when the toolchain does, which shows up
# as a spurious diff nobody can explain. Built with:
#
#   pandoc 3.9
#   tectonic 0.15.0
#
# A different pandoc or fvextra will produce a different .tex for the same
# source. If you see an unexplained diff in the generated files, check these
# first.

set -euo pipefail

[ $# -ge 1 ] || { echo "usage: $0 <input.md> [output-dir]" >&2; exit 2; }

SRC=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
[ -f "$SRC" ] || { echo "no such file: $SRC" >&2; exit 2; }

NAME=$(basename "$SRC" .md)
OUTDIR=${2:-$(dirname "$SRC")}
mkdir -p "$OUTDIR"

TEX="$OUTDIR/$NAME.tex"
PDF="$OUTDIR/$NAME.pdf"
DOCX="$OUTDIR/$NAME.docx"

MAINFONT="Arial Unicode MS"
MONOFONT="Menlo"

LOG=$(mktemp)
BODY=$(mktemp /tmp/md2pdf.XXXXXX.md)
FLAG=$(mktemp)
trap 'rm -f "$LOG" "$BODY" "$FLAG"' EXIT

python3 "$(dirname "$0")/md2pdf_body.py" "$SRC" "$BODY" "$FLAG"
SHIFT=$(cat "$FLAG")

COMMON=(--from=markdown --standalone --no-highlight
        -V mainfont="$MAINFONT" -V monofont="$MONOFONT"
        -V fontsize=10pt)

# The document's own H1 became the title and was removed from the body, so
# promote what is left: the former H2s become sections 1, 2, 3 rather than
# subsections of a section that no longer exists.
[ "$SHIFT" = yes ] && COMMON+=(--shift-heading-level-by=-1)

pandoc "$BODY" "${COMMON[@]}" -o "$TEX" 2>"$LOG"
pandoc "$BODY" "${COMMON[@]}" --pdf-engine=tectonic -o "$PDF" 2>>"$LOG"

# Word reflows text itself, so it needs neither the wrapping workarounds nor
# the font overrides — and it keeps the syntax highlighting the PDF gives up.
DOCX_OPTS=(--from=markdown --standalone --toc)
[ "$SHIFT" = yes ] && DOCX_OPTS+=(--shift-heading-level-by=-1)
pandoc "$BODY" "${DOCX_OPTS[@]}" -o "$DOCX" 2>>"$LOG"

if grep -q "Missing character" "$LOG"; then
  echo "FAIL: glyphs dropped — the PDF would render with holes." >&2
  grep "could not represent character" "$LOG" | sort -u >&2
  exit 1
fi

OVERFULL=$(grep -c "Overfull" "$LOG" || true)

echo "$NAME -> $OUTDIR"
printf '  %-34s %8s bytes\n' "$(basename "$TEX")"  "$(wc -c < "$TEX"  | tr -d ' ')"
printf '  %-34s %8s bytes  (overfull: %s, title-shift: %s)\n' \
       "$(basename "$PDF")" "$(wc -c < "$PDF" | tr -d ' ')" "${OVERFULL:-0}" "$SHIFT"
printf '  %-34s %8s bytes\n' "$(basename "$DOCX")" "$(wc -c < "$DOCX" | tr -d ' ')"
