# LakeForcing

**An open pipeline that turns open global data into hydrodynamic + wind-wave forcing
for *any* inland lake, to drive [OpenDrift](https://opendrift.github.io/) Lagrangian
particle tracking.**

Built with **Delft3D-FLOW + Delft3D-WAVE** and exported as **CF-compliant NetCDF**.
The methodological core is the **σ-layer → z-level coupling** that makes
terrain-following Delft3D output readable by OpenDrift's fixed-depth reader.

> Companion code for the manuscript *"LakeForcing: a σ-to-z coupling algorithm and
> open pipeline for hydrodynamic and wind-wave forcing of inland lakes to drive Lagrangian
> transport models"*
> (target: **Computers & Geosciences**; a companion dataset descriptor for *Data in Brief*
> is planned). Draft: `paper/CAGEO_manuscript.md`.

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
**Demonstrated** on **12 lakes** on all inhabited continents (36°S → 60°N; shallow ↔ deep;
natural ↔ reservoir; two bathymetry sources), all through the same unmodified pipeline. The
results establish physical plausibility and internal consistency (plus a model-to-model
benchmark and an independent satellite surface-temperature check), not per-lake validation
against in-situ observations. See `output/figure_demonstration.png`,
`paper/CAGEO_manuscript.md` Table 3, and `docs/figure_architecture.png`.

## Requirements
Python 3.11 (`requirements.txt`, pinned; conda-forge recommended so `rasterio`/`pyproj` bind a
consistent GDAL/PROJ) + **Delft3D 4.07.01** (FLOW + WAVE/SWAN, installed separately) + an ERA5 CDS
account (`~/.cdsapirc`). OpenDrift is pinned to **1.14.9**. The reported 12-lake runs were produced
on **Windows 11 (64-bit)**; the pipeline also runs on 64-bit Linux.

### Delft3D engine (reproducing the hydrodynamic runs)
The runs used the **official Deltares pre-built Delft3D 4 binary, release tag `4.07.01`**, from the
Deltares open-source portal (<https://oss.deltares.nl/web/delft3d>), launched through its own batch
scripts — **not** a local source build, so results do not depend on a user's compiler/MPI/patch
level. Only the σ-to-z **exporter** is needed to reproduce the headline result, and it runs with no
Delft3D install (see *Reproducible test* below).

### ERA5 retrieval (Copernicus CDS)
`get_era5*.py` call `cdsapi` against dataset **`reanalysis-era5-single-levels`**,
`product_type: reanalysis`, with variables:
- wind: `10m_u_component_of_wind`, `10m_v_component_of_wind`
- heat flux: `2m_temperature`, `2m_dewpoint_temperature`, `total_cloud_cover`, `surface_solar_radiation_downwards`
- mass balance: `total_precipitation`, `evaporation`, `2m_temperature`

Create a free CDS account, accept the ERA5 licence, and write your key to `~/.cdsapirc`. The new
Climate Data Store (CDS-Beta) replaced the legacy endpoint in 2024–2025; install a `cdsapi`
compatible with the current endpoint (the variable names above are unchanged across the migration —
only the endpoint URL and key differ).

### Reproducible test (no Delft3D needed)
`pytest tests/test_cf_export.py` runs the σ-to-z exporter on a versioned, checksummed **Erken**
fixture (`tests/fixtures/trim-erken_mini.nc`, 125×52 grid, 14 σ-layers, 2 time steps, EPSG:32634;
`wavm-erken_mini.nc`), built by `tests/build_fixture.py`, and asserts CF compliance and the headline
variables. This also runs in GitHub-Actions CI.

### Rebuilding the manuscript
The submission `.docx` is generated from source: `python src/build_docx.py` renders
`paper/CAGEO_manuscript.md` (equations as native OMML via `src/omml_equations.py`; figures from
`src/make_figures.py`) to `paper/CAGEO_manuscript_VP.docx`.

## Data & licence
- **Code:** MIT (`LICENSE`).
- **Generated forcing dataset** (`output/*_forcing.nc`): CC-BY-4.0.
- **Inputs** retain their own licences/citations: HydroLAKES, GLOBathy, DAHITI, ERA5.

## Cite
See `CITATION.cff`. Archived on Zenodo: [10.5281/zenodo.20627160](https://doi.org/10.5281/zenodo.20627160).
