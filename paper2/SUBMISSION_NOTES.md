# Earth Science Informatics (Springer) — submission package

Backup submission, prepared in parallel with the Computers & Geosciences package in
`../paper/`. The **science is identical** — the manuscript here is built from the same
shared source (`paper/CAGEO_manuscript.md`) via `src/build_esi.py`, so any change to the
manuscript propagates to both packages on rebuild.

## Files
| File | Purpose |
|---|---|
| `ESInformatics_manuscript.docx` | Full manuscript (Times New Roman, embedded figures, native Word equations, line numbers) |
| `CoverLetter.docx` | Cover letter addressed to the Editors-in-Chief, Earth Science Informatics |
| `GraphicalAbstract.png` | Optional graphical abstract (Springer accepts one; reused from the C&G package) |

## What differs from the Computers & Geosciences package
- **Cover letter** re-addressed to *Earth Science Informatics* and re-scoped to the
  *computer science × geosciences* interface (ESI's remit). No other text changes were
  needed — the manuscript is already journal-agnostic and method-forward.
- **No Highlights file.** Highlights are an Elsevier device; Springer does not use them.
- Everything else (title, abstract, figures, references, declarations) is unchanged.

## Springer / ESI submission checklist
- **Submission system:** Editorial Manager (Springer). Article type: *Research Article*
  (software / methodological contribution).
- **Title page / authors / affiliation:** present in the manuscript front matter.
- **Abstract:** ~148 words, unstructured — within Springer's typical ≤250-word limit.
- **Keywords:** 6, present.
- **Declarations** (Springer expects these; the manuscript already carries them as
  end sections — Editorial Manager may also ask for them in form fields):
  - *Funding* — "no specific grant; CERTH-ITI infrastructure" (Funding section).
  - *Competing interests* — none (Declaration of competing interest).
  - *Author contributions* — CRediT statement (V.P., C.G.E.A., A.M., I.G., S.V., I.K.).
  - *Data availability* — GitHub + Zenodo (Data availability section).
  - *Code availability* — same GitHub repo (MIT) + Zenodo archive; ESI weighs this
    heavily. If the form asks for a *separate* Code-availability statement, reuse:
    "Open source (MIT) at https://github.com/vaspapa79/LakeForcing, archived at
    https://doi.org/10.5281/zenodo.20627160."
  - *Ethics approval / Consent* — not applicable (no human/animal subjects).
- **Open code/data (mandatory-ish for ESI):** public GitHub repo + Zenodo DOI, a CI test
  on a bundled fixture, MIT licence, documented README — all already in place.
- **Reference style:** Springer is flexible at submission; the current author–year format
  is fine. If accepted, convert to *Springer Basic* (name–year) if requested.
- **Suggested reviewers (optional):** can be drawn from the reference list (e.g. authors of
  the OpenDrift / Parcels / lake-modelling / GMD papers).

## Rebuild
```
python src/build_esi.py    # regenerates ESInformatics_manuscript.docx + CoverLetter.docx
```
