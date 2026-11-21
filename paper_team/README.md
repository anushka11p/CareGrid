# CareGrid team paper (draft)

`main.tex` is an IEEE conference draft for Khrisha N, Anushka Prasad, Pushpa Mitra Ganesh (equal contribution)
and Dr. P. Madhavan (corresponding). It is a starting point to rewrite in your own words, not a final text.

## Build
```
python paper_team/make_paper.py     # from the project root: figures, tables, facts.json from the results
cd paper_team && tectonic -X compile main.tex
```
Word: `python paper_team/make_docx.py` writes `CareGrid_paper.docx` in IEEE conference layout (US Letter,
two columns, numbered equations, editable Word equations). Needs pandoc. Re-running it overwrites the file,
so rewrite in a copy.
Overleaf: upload `CareGrid_paper_overleaf.zip` (main.tex, refs.bib, tab_*.tex, fig_*.pdf) and compile with pdfLaTeX.

## Where each number comes from
- `tab_*.tex` and `fig_*.pdf` are generated; do not edit them by hand, change `make_paper.py`.
- Numbers in the text come from `facts.json` (also generated) and the step folders in `../personC/`.
  If you re-run any experiment, re-run `make_paper.py` and check the text against `facts.json`.

## Before submission
- Rewrite the text, keep the numbers.
- Fill in: repository link, author contribution statement, acknowledgments (funding; AI-use disclosure if the venue asks).
- Check the target venue's page limit and template.
