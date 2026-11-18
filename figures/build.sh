#!/usr/bin/env bash
# Typeset the TikZ data-flow figures and publish them to public/images/<name>.png.
#
#   ./figures/build.sh                          # all *.tex in figures/
#   ./figures/build.sh alg_dataflow_tan_slide   # just one
#
# Requires: pdflatex (TikZ) and pdftoppm (poppler). PNGs at 200 dpi.
# *_slide.tex are the slide versions (no prose above the step headers or under the
# legend; the slide carries the caption) and are published without the suffix:
# alg_dataflow_tan_slide.tex -> public/images/alg_dataflow_tan.png. The paper versions
# (alg_dataflow_tan.tex, ...) are published as <name>_paper.png.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
out="$here/../public/images"
build="$here/build"
mkdir -p "$out" "$build"

if [ $# -gt 0 ]; then
  targets=("$@")
else
  targets=()
  for f in "$here"/*.tex; do targets+=("$(basename "$f" .tex)"); done
fi

for t in "${targets[@]}"; do
  echo "== $t"
  pdflatex -interaction=nonstopmode -halt-on-error -output-directory "$build" "$here/$t.tex" > "$build/$t.log"
  case "$t" in
    *_slide) name="${t%_slide}" ;;
    alg_dataflow_v42) name="$t" ;;
    *) name="${t}_paper" ;;
  esac
  pdftoppm -png -r 200 -singlefile "$build/$t.pdf" "$out/$name"
  echo "   -> public/images/$name.png"
done
