# Computers & Geosciences framing: positioning vs existing approaches

*(Draft for the Computers & Geosciences manuscript — the "why this is
new" spine. Figure: docs/figure_architecture.png.)*

## The gap
Lagrangian transport modelling in **inland lakes** — floating plastics, oil spills,
harmful-algal-bloom material, fish larvae — needs gridded **current and wind-wave
forcing**. For the ocean this is routine: global reanalyses (CMEMS/Copernicus) feed
particle trackers like OpenDrift directly. For lakes it is not: global ocean products
**stop at the coastline**, and lake-specific hydrodynamic models are built by hand,
one lake at a time, with bespoke grids and forcing. As a result, most lake transport
studies either reuse a single hand-tuned model or fall back on idealised/analytical
flow fields. There is **no open, reproducible workflow** that turns globally available
data into transport-model-ready lake forcing.

## What we contribute
An open Python pipeline (Fig. 1) that, for **any lake**, assembles bathymetry and
meteorology from **open global sources** (HydroLAKES/GLOBathy/DAHITI; ERA5), generates
a **Delft3D-FLOW + Delft3D-WAVE** setup automatically, and exports **CF-compliant
NetCDF** that drives **OpenDrift** unchanged. It is demonstrated across a
morphologically and climatically diverse set of lakes (shallow lowland → deep
peri-alpine; natural → reservoir; 8°N tropical → 60°N boreal).

## Positioning

| Existing approach | Limitation for lake transport | How this pipeline differs |
|---|---|---|
| **CMEMS / global ocean reanalyses → OpenDrift** | coverage ends at the coast; no inland lakes | produces forcing for any lake from open data |
| **Hand-built per-lake Delft3D/FVCOM/SCHISM models** | labour-intensive, non-reproducible, not transferable | auto-generates the model setup from open inputs |
| **OpenDrift native readers (ROMS, generic)** | no Delft3D reader; σ-coordinate fields are not ingestible | `cf_export` bridges Delft3D σ-layers → OpenDrift z-levels |
| **GLOBathy / HydroLAKES** | static bathymetry only — no dynamic forcing | adds physically-based currents + waves on that bathymetry |
| **Idealised / analytical lake flow** | not data-driven; no waves/Stokes; no heat | physics-based FLOW+WAVE with real ERA5 meteo + Stokes drift |

## The methodological core (the reviewer hook)
The reusable novelty is the **σ→z coupling** in `cf_export`: Delft3D-FLOW writes
velocities on terrain-following σ-layers whose depth varies in space and time, while
OpenDrift expects fixed metric z-levels. The export reconstructs each σ-layer's true
depth from the instantaneous water level and bathymetry, vertically regrids to fixed
z (clamping the shallowest layer to the free surface so floating particles are
represented), interpolates the curvilinear grid to a regular lon/lat raster, rotates
grid-oriented velocities to east/north, and derives surface Stokes drift from the wave
field. To our knowledge this Delft3D→OpenDrift coupling has not been published as a
generalised, lake-agnostic workflow.

## Honest limitations (state up front)
- space-uniform wind per lake (ERA5 single point); fine for small/medium lakes, a
  caveat for very large ones (Great-Lakes scale).
- stationary-SWAN option in the demo (a time-varying wave run is supported but heavier).
- ERA5 ~0.25° / ~9 km meteorology.
- freshwater density approximation (salinity reference 0) — not for hypersaline lakes
  without modification.
- DAHITI bathymetry captures the satellite-observed depth band, not necessarily the
  full maximum depth.
