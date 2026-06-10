# LakeForcing-OpenDrift

**An open pipeline that turns open global data into hydrodynamic + wind-wave forcing
for *any* inland lake, to drive [OpenDrift](https://opendrift.github.io/) Lagrangian
particle tracking.**

Built with **Delft3D-FLOW + Delft3D-WAVE** and exported as **CF-compliant NetCDF**.
The methodological core is the **σ-layer → z-level coupling** that makes
terrain-following Delft3D output readable by OpenDrift's fixed-depth reader.

> Companion code for the manuscript *"An open pipeline for generating hydrodynamic and
> wind-wave forcing of inland lakes to drive Lagrangian transport models"*
> (target: **Environmental Modelling & Software**; dataset descriptor backup: *Data in
> Brief*). Draft: `paper/EMS_manuscript.md`.

## Why
Global ocean reanalyses (CMEMS) stop at the coast, so lake-scale transport modelling
(plastics, oil, HABs, larvae) has no ready forcing. Lake models are usually hand-built
one at a time. This pipeline removes that bottleneck: give it a lake location, it
assembles bathymetry + meteorology from open data, auto-configures and runs Delft3D,
and emits OpenDrift-ready forcing.

## Pipeline (`src/`)
```
HydroLAKES/GLOBathy/DAHITI bathymetry ─┐
ERA5 meteorology                       ┼─►  per-lake forcing  ─►  OpenDrift
KMZ survey contours                    ─┘
```
| Module | Role |
|---|---|
| `ingest_bathy_kmz.py` / `dahiti_bathymetry.py` / `gebco_subset.py` | acquire bathymetry |
| `build_grid.py` | bathymetry → Delft3D curvilinear grid (`.grd/.dep/.enc`), CCW (FLOW+WAVE) |
| `get_era5.py` / `get_era5_tem.py` / `get_era5_eva.py` | ERA5 → wind / heat / evap-precip files |
| `make_flow_mdf.py` / `make_wave_mdw.py` | closed-lake FLOW `.mdf` + WAVE `.mdw` + run config |
| **`cf_export.py`** | **σ→z + curvilinear→lon/lat + velocity rotation + Stokes → CF-NetCDF** |
| `run_opendrift_demo.py` | OpenDrift transport demo (inland-lake config) |
| `setup_lake.py` | one-command staging of a lake (grid+forcing+mdf+mdw) |
| `postprocess_lake.py` | cf_export → OpenDrift → drift stats for one lake |
| `figure_demonstration.py` | multi-lake demonstration figure |

## Quick start (one lake)
```bash
# 1. stage everything from open data (needs ~/.cdsapirc for ERA5)
python src/setup_lake.py --prefix erken --srckey erken_sweden \
    --lon 18.572 --lat 59.845 --tzone 2 --t0 15
# 2. run Delft3D FLOW then WAVE  (engine installed separately)
models/erken/run_flow_wave.bat
# 3. couple to OpenDrift-ready forcing + demo transport
python src/postprocess_lake.py --prefix erken
# -> output/erken_forcing.nc  +  output/erken_trajectory.nc
```

## Demonstration
Validated on **12 lakes** on all inhabited continents (36°S → 60°N; shallow ↔ deep;
natural ↔ reservoir; two bathymetry sources), all through the same unmodified pipeline.
See `output/figure_demonstration.png`, `paper/EMS_manuscript.md` Table 3, and
`docs/figure_architecture.png`.

## Requirements
Python 3.11 (`requirements.txt`) + **Delft3D 4.07.01** (FLOW + WAVE/SWAN, installed
separately) + an ERA5 CDS account (`~/.cdsapirc`). OpenDrift 1.14.9.

## Data & licence
- **Code:** MIT (`LICENSE`).
- **Generated forcing dataset** (`output/*_forcing.nc`): CC-BY-4.0.
- **Inputs** retain their own licences/citations: HydroLAKES, GLOBathy, DAHITI, ERA5.

## Cite
See `CITATION.cff`. Archived on Zenodo: [10.5281/zenodo.20627161](https://doi.org/10.5281/zenodo.20627161).
