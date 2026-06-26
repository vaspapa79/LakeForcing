# LakeForcing v1.2.1 — Computers & Geosciences revision round

Revision of the LakeForcing pipeline and manuscript addressing the *Computers & Geosciences*
major-revision report (review v01). No change to the σ-to-z algorithm or the twelve-lake results;
the changes improve reproducibility, provenance and the honesty of the data/benchmark framing.

## What changed

**Reproducibility & provenance**
- README now documents the exact Delft3D acquisition (official Deltares pre-built Delft3D 4 binary,
  release tag `4.07.01`, Windows 11 64-bit — no local source build), so results do not depend on a
  user's compiler/MPI/patch level.
- README documents the ERA5/Copernicus CDS retrieval: dataset `reanalysis-era5-single-levels`,
  `product_type: reanalysis`, the exact variable short-names, credential setup (`~/.cdsapirc`) and
  the CDS-Beta migration note.
- `requirements.txt` (pinned; `opendrift==1.14.9`, conda-forge recommended) referenced from the
  paper and README.
- CI fixture (`tests/fixtures/`) provenance documented: an Erken subset (125×52 grid, 14 σ-layers,
  2 steps, EPSG:32634) built by `tests/build_fixture.py`, with the exporter assertions listed.

**Data availability (corrects review item R5)**
- The forcing dataset is **not** embedded in the Zenodo software archive (which archives the code
  snapshot only, via the GitHub-release integration). It is distributed as this **release asset**:
  `LakeForcing-OpenDrift_forcing_dataset_v1.0.0.zip` (~0.7 GB; twelve `<lake>_forcing.nc`,
  ~0.9 GB uncompressed), CC-BY-4.0.
- `output/DATASET_MANIFEST.txt` lists each file's size and **SHA-256** checksum for verification
  against Section 4 of the paper.

**Manuscript**
- §5.6 reframed as a same-group model-to-model *consistency check* (not independent validation).
- Conservation discrepancy reported across the depth range; area–drift correlation reported with and
  without the hand-built lake.
- SWAN field names (`HSIGN`/`RTP`/`DIR`), σ-layer variable/sign convention, satellite-comparison
  methodology, and the exposed `Z_LEVELS` parameter all specified.
- Point-by-point `paper/Response_to_Reviewers.docx` and refreshed `paper/CoverLetter.docx`.

## Citation / DOI
The Zenodo **concept DOI** is unchanged: https://doi.org/10.5281/zenodo.20627160 (always resolves to
the latest version). Publishing this release adds a new version under the same concept DOI.

## Release assets to attach
- `LakeForcing-OpenDrift_forcing_dataset_v1.0.0.zip` (the twelve-lake forcing dataset, CC-BY-4.0)
- `output/DATASET_MANIFEST.txt` (sizes + SHA-256)
