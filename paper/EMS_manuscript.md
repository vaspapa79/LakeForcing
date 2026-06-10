# LakeForcing-OpenDrift: an open, reproducible pipeline for generating hydrodynamic and wind-wave forcing of inland lakes to drive Lagrangian transport models

Vassilios Papaioannou^1,\*, Christos Anagnostopoulos^1, Anastasia Moumtzidou^1, Ilias Gialampoukidis^1, Stefanos Vrochidis^1, Ioannis Kompatsiaris^1

^1 Information Technologies Institute, Centre for Research and Technology Hellas (CERTH-ITI), 6th km Charilaou-Thermi, 57001 Thessaloniki, Greece

\*Corresponding author: Vassilios Papaioannou, vaspapa@iti.gr, Tel. +30 697 285 4287

---

## Abstract
Lagrangian particle tracking is a standard tool for studying the transport and fate of
floating material — plastics, oil, harmful-algal-bloom cells, fish larvae — and recent
cross-national surveys show that inland lakes and reservoirs are among the most acutely
plastic-polluted freshwater systems on Earth, in places exceeding oceanic "garbage
patches" (Nava et al., 2023; Chen et al., 2024). Yet lake-scale transport modelling is
hampered by the absence of ready-made forcing: global ocean reanalyses are masked to the
marine domain, and lake hydrodynamic models are still built by hand, one waterbody at a
time. We present LakeForcing-OpenDrift, an open and reproducible Python pipeline that
assembles bathymetry and meteorology from open global sources, automatically configures
and runs a coupled Delft3D-FLOW + Delft3D-WAVE (SWAN) simulation for an arbitrary
lake, and exports CF-compliant NetCDF that drives the OpenDrift particle tracker
without modification. The methodological core is a transform that bridges Delft3D's
terrain-following σ-layers to OpenDrift's fixed metric z-levels, combined with the
curvilinear→regular regridding, grid-to-geographic velocity rotation and surface
Stokes-drift derivation needed to make lake hydrodynamics ingestible by a generic ocean
particle tracker. We give the full governing relations, document the automated
closed-lake model generation, and demonstrate the pipeline on twelve lakes spanning a wide
morphological and climatic range across all inhabited continents — from 36°S to 60°N,
shallow to deep, tropical to boreal — all processed through the same unmodified code. The
simulated 36-h surface transport spans an order of magnitude (0.34–3.7 km) and is
physically consistent with each lake's size, depth, fetch and wind exposure. The complete
toolchain and the generated twelve-lake forcing dataset are released openly under
permissive licences, removing the
forcing bottleneck for lake-scale transport studies.

**Keywords:** Lake hydrodynamics; Wind-wave modelling (SWAN); Sigma-to-z coupling;
OpenDrift; Lagrangian particle tracking; Reproducible open-source workflow

---

## Code metadata

| | |
|---|---|
| Current code version | v1.0.1 |
| Permanent link to code / repository | https://github.com/vaspapa79/LakeForcing-OpenDrift (archived on Zenodo with a citable DOI on release) |
| Permanent link to reproducible capsule | Not applicable |
| Legal code licence | MIT (source code); CC-BY-4.0 (generated forcing dataset) |
| Code versioning system used | git |
| Software code languages, tools and services used | Python 3.11; Delft3D 4.07.01 (FLOW + WAVE/SWAN, external engine); ERA5 (Copernicus CDS); HydroLAKES; GLOBathy; DAHITI |
| Compilation requirements, operating environments and dependencies | xarray, numpy, scipy, pyproj, rasterio, netCDF4, cdsapi, matplotlib, cartopy; OpenDrift 1.14.9; Windows or Linux |
| Link to developer documentation / manual | Repository README and the present manuscript |
| Support email for questions | vaspapa@iti.gr |

---

## 1. Introduction

Lagrangian particle-tracking models such as OpenDrift (Dagestad et al., 2018) and Parcels
(Delandmeter and van Sebille, 2019) are now standard tools for simulating the transport
and fate of floating material — plastic debris, spilled oil, harmful-algal-bloom cells,
fish eggs and larvae — in aquatic environments. In these models the velocity of a buoyant
particle is reconstructed as the vector sum of the Eulerian near-surface current, a
wind-induced windage term, and the wave-driven Stokes drift (van den Bremer and Breivik,
2018). The Stokes contribution is not a second-order correction: under realistic wind-sea
conditions it can account for a large fraction of the net surface displacement, and
omitting it systematically biases predicted transport pathways and accumulation zones
(Kukulka et al., 2012; Onink et al., 2019; van Sebille et al., 2020). In the open ocean
all three contributions are supplied operationally: gridded current, wind and spectral-wave
products from services such as the Copernicus Marine Service are ingested directly by the
tracker, so that the modelling task reduces to specifying the particle physics rather than
producing the forcing.

Inland waters break this workflow. Lakes and reservoirs hold the large majority of the
planet's liquid surface freshwater (Messager et al., 2016) and act as acute receptors of
plastic pollution, oil spills, harmful algal blooms and a range of ecological transport
processes. The first standardised cross-national survey of lake plastic debris detected
contamination in every one of 38 lakes and reservoirs sampled, with surface concentrations
in the most affected systems exceeding those reported for oceanic accumulation zones (Nava
et al., 2023); complementary global meta-analyses document pervasive microplastic pollution
across lakes in 43 countries and identify lake morphometry and hydraulic residence time as
primary controls on retention (Wagner et al., 2014; Chen et al., 2024). Quantifying where
this material accumulates demands the same Lagrangian machinery used in the ocean — yet the
forcing that machinery depends on is unavailable off the shelf for lakes, for three
structural reasons.

First, global ocean reanalyses are masked to the marine domain: their land–sea masks
terminate at the coastline and carry no information inside continental waterbodies, so for
an inland lake there is simply nothing to read. Second, three-dimensional lake hydrodynamic
models are well established and extensively validated (Wüest and Lorke, 2003; Hipsey et al.,
2019; Ishikawa et al., 2022), but they are almost always assembled by hand for a single
waterbody — with a bespoke computational grid, hand-set bathymetry, and site-specific
boundary and forcing conditions — so the effort is labour-intensive and non-transferable,
and each new lake restarts it from scratch. Third, where this cost is avoided, modellers
commonly substitute idealised or analytical flow fields that omit waves, Stokes drift and
thermally driven circulation, precisely the processes that dominate the surface transport
one is trying to resolve.

The net effect is a forcing bottleneck: the particle tracker itself is mature, open and
free, but generating physically complete, transport-ready fields to drive it for an
arbitrary lake remains the rate-limiting step. Existing inland-water transport frameworks
narrow this gap without closing it; the TELEMAC-coupled CaMPSim-3D system (Pilechi et al.,
2022), for example, couples three-dimensional hydrodynamics to particle transport with
demonstrable skill, but remains tied to a specific hydrodynamic engine and configured per
study site. To our knowledge no open, reproducible workflow exists that converts globally
available data into transport-model-ready lake forcing — wind-waves and Stokes drift
included — in a manner that is simultaneously lake-agnostic and decoupled from any single
tracker.

This paper presents such a workflow. Given only a lake's geographic coordinates, the
pipeline assembles bathymetry from open global datasets (HydroLAKES, Messager et al., 2016;
GLOBathy, Khazaei et al., 2022) or from satellite-altimetry products where in-situ surveys
are absent (DAHITI, Schwatke et al., 2015), and atmospheric forcing from the ERA5 reanalysis
(Hersbach et al., 2020); it then automatically constructs and runs a coupled Delft3D-FLOW
(Lesser et al., 2004) and Delft3D-WAVE/SWAN (Booij et al., 1999) simulation of the closed
basin, and exports CF-compliant NetCDF that OpenDrift reads without modification. The
central technical obstacle it resolves is a coordinate incompatibility: Delft3D-FLOW
discretises the vertical with terrain-following σ-layers whose physical depth varies in
space and time with the free surface and the bed, whereas OpenDrift's generic reader expects
fields sampled on fixed metric z-levels. As recent inter-comparisons of vertical-coordinate
choices for lakes emphasise (Ishikawa et al., 2022), reconciling the two representations is
non-trivial, and without it Delft3D output cannot be ingested by the generic reader at all.
We close this gap with an explicit, fully specified σ→z coupling that additionally carries
the curvilinear-to-geographic velocity rotation and the surface Stokes-drift derivation
needed to render lake hydrodynamics ingestible by an ocean-oriented tracker.

Table 1 situates the pipeline against the alternatives currently used for lake transport
modelling. Its reusable novelty is the σ→z coupling: we are not aware of any published,
generalised, lake-agnostic Delft3D→OpenDrift workflow that also propagates the wave-driven
Stokes drift.

**Table 1.** Positioning of the proposed pipeline relative to existing approaches to lake
transport forcing.

| Existing approach | Limitation for lake transport | This pipeline |
|---|---|---|
| Global ocean reanalyses (CMEMS) → OpenDrift | coverage ends at the coast | forcing for any lake from open data |
| Hand-built per-lake hydrodynamic models | labour-intensive, non-reproducible | auto-generates the setup from open inputs |
| 1-D vertical lake models (e.g. GLM) | no horizontal transport field | full 3-D currents + waves on a grid |
| Site-specific transport frameworks (e.g. CaMPSim-3D) | configured per site and per engine | engine output exported to a generic CF reader |
| OpenDrift native readers (ROMS, generic) | no Delft3D reader; σ-fields not ingestible | σ→z coupling bridges the gap |
| GLOBathy / HydroLAKES | static bathymetry only | adds physics-based currents + waves |
| Idealised / analytical lake flow | no data, no waves/Stokes, no heat | data-driven FLOW+WAVE + Stokes |

The specific contributions of this work are: (i) an open, end-to-end pipeline from open
global data to OpenDrift-ready lake forcing; (ii) a reusable, fully specified σ→z coupling
that simultaneously carries currents, temperature, water level and the wave-driven Stokes
drift; (iii) automated generation of closed-lake Delft3D models from open inputs; and (iv) a
demonstration of generality across twelve morphologically and climatically diverse lakes
spanning all inhabited continents, processed by identical code. The remainder of the paper
is organised as follows: Section 2 develops the theory and governing equations of the
coupling; Section 3 describes the software architecture and modules; Section 4 details the
illustrative application and its physical configuration; Section 5 presents and discusses
the twelve-lake results; and Sections 6 and 7 set out limitations and conclusions.

---

## 2. Theory and methods

This section sets out the theory underpinning the pipeline and the governing relations it
implements. We first outline the end-to-end workflow and the file-based contracts that link
its stages (Section 2.1), then describe how an open-data lake description is turned into a
Delft3D-ready grid (Section 2.2), how the atmospheric forcing is assembled from reanalysis
(Section 2.3), and how a closed-lake model is configured automatically (Section 2.4). The
methodological core follows in Section 2.5, which specifies the σ-layer → z-level coupling
together with the curvilinear-to-geographic velocity rotation and the surface Stokes-drift
derivation that render Delft3D output ingestible by OpenDrift. Section 2.6 defines the
transport demonstration used to exercise the resulting forcing. Throughout, the governing
relations given are those actually evaluated in the released code, so that the description
is reproducible rather than merely indicative.

### 2.1 Pipeline overview

The pipeline (Fig. 1) is implemented as a chain of single-purpose Python modules coupled
exclusively through standard on-disk file formats rather than through shared in-memory
state. This file-based contract is deliberate: every stage reads named input files and
writes named output files, so each stage can be executed, inspected, cached or replaced in
isolation, and any failure is localised to the artefact it produces rather than propagating
silently through a monolithic run. From a single lake location, processing advances through
five sequential stages, each consuming the artefacts written by the previous one:

- Grid construction ingests bathymetry and emits the Delft3D curvilinear grid triple
  (.grd geometry, .dep depths, .enc enclosure).
- Meteorological forcing queries the ERA5 reanalysis and writes the Delft3D time-series
  files for wind, surface heat exchange and the evaporation–precipitation mass balance.
- Automated model generation combines the grid and forcing into a complete FLOW master
  definition (.mdf) and a WAVE/SWAN control file (.mdw) together with their run
  configuration.
- Coupled simulation executes Delft3D-FLOW and Delft3D-WAVE/SWAN, producing the native
  terrain-following σ-coordinate current, water-level and temperature fields and the
  spectral-wave parameters.
- Coupling and export applies the σ→z transform, velocity rotation and horizontal
  regridding of Section 2.5 to emit a single CF-compliant NetCDF, optionally followed by
  the OpenDrift transport demonstration.

Two design goals shape this decomposition. First, the common case — a closed lake with no
regulated open boundaries and no river discharges — must run end-to-end without manual
intervention, because the hand editing of model control files is historically the most
error-prone step in lake-model setup. Second, the general case must remain fully
accessible: because every intermediate artefact is a standard, self-describing file, a
user can inspect it, override it, or inject an external product — a surveyed grid, a
hand-tuned .mdf, or the raw output of a pre-existing Delft3D model — at the corresponding
stage without altering the surrounding code. The exporter, in particular, depends only on
the engine output and not on how the run was configured, so it can be applied even to
Delft3D models the pipeline did not generate (Section 3.2).

[[FIG:architecture]]

### 2.2 Grid construction

Grid construction maps raw bathymetric data onto a Delft3D-compatible curvilinear grid
through three operations — ingestion, projection and interpolation — and is the only stage
whose inputs differ substantially between lakes. Bathymetry enters in one of two forms. In
the first, per-depth shoreline contours digitised into a KMZ file are decoded into a
`(lon, lat, depth)` point cloud, with every vertex of a contour assigned that contour's
labelled depth. In the second, a gridded bed-elevation raster (a DAHITI- or
GLOBathy-derived GeoTIFF) is read with windowed, decimated input/output: only the window
covering the lake's bounding box is read, and it is downsampled on read, so that
continental-scale source tiles are subset and coarsened during loading and peak memory use
stays bounded independently of the source-tile size.

The ingested points are projected from geographic coordinates to the Universal Transverse
Mercator zone containing the lake centroid, yielding a locally isometric metric frame in
which horizontal distances are undistorted and grid cells are close to square. A regular,
axis-aligned curvilinear grid is then laid over the lake's bounding box at a cell size
scaled to the basin's longer horizontal axis, so that lakes differing by orders of
magnitude in surface area are resolved with a comparable cell count — of order tens of
metres for kilometre-scale basins, coarsening for the largest lakes — keeping the node
count within the engine's practical limits while still resolving the dominant shoreline
geometry. Bed depth is interpolated from the point cloud onto the grid nodes; for raster
inputs the still-water depth is obtained as the difference `surface_level − bed_elevation`,
following the Delft3D convention of positive-downward depths referenced to the still-water
level. Grid nodes whose interpolated position lies outside the digitised shoreline are
flagged as dry in the enclosure (`.enc`) file, which fixes the active computational domain
and excludes land cells from the solution.

A single orientation constraint governs the entire construction: the grid is generated
counter-clockwise. Delft3D-FLOW accepts either handedness, but the SWAN wave solver
requires a counter-clockwise grid; emitting one counter-clockwise grid therefore allows the
identical grid to drive both engines, which removes a grid-to-grid interpolation step and
eliminates an entire class of FLOW–WAVE orientation-mismatch errors that would otherwise
have to be diagnosed by hand.

### 2.3 Meteorological forcing

Three modules retrieve ERA5 hourly fields (Hersbach et al., 2020) sampled at the lake
centroid and translate them into the three time-series forcing files Delft3D-FLOW expects.
The first writes the wind forcing. From the ERA5 eastward and northward 10 m components
`u10` and `v10`, the scalar wind speed is the Euclidean magnitude

[[EQ:windspeed]]

while the direction is converted to the nautical (meteorological, "blowing-from")
convention that Delft3D requires,

[[EQ:winddir]]

where negating both velocity components inside the four-quadrant arctangent maps the
mathematical "blowing-towards" vector angle onto the meteorological "coming-from" bearing,
and the modulo confines the result to the interval [0°, 360°).

The second module writes the heat-flux forcing that drives the Ocean heat-flux model
(Delft3D heat model 5): relative humidity, 2 m air temperature, total cloud cover and net
shortwave radiation. ERA5 provides temperature and dewpoint rather than humidity directly,
so relative humidity is reconstructed from the 2 m air temperature `Ta` and dewpoint `Td`
(in °C) as the ratio of saturation vapour pressures given by the improved Magnus
approximation,

[[EQ:magnus]]

in which the coefficients `a = 17.625` and `b = 243.04` °C are the least-squares-optimised
Magnus constants of Alduchov and Eskridge (1996); this parameterisation keeps the
saturation-pressure error below 0.4 % over the −40 to +50 °C range that spans realistic
lake-surface and air conditions, and is therefore preferable to the older Magnus–Tetens
constants.

The third module writes the evaporation–precipitation forcing — precipitation, evaporation
and rain temperature — that closes the surface water-mass balance. All three series share a
single timing convention imposed by the Delft3D time-dependent-data reader: each is
referenced to the model start epoch in the lake's local time zone and clipped to begin
exactly at the simulation start, because the reader aborts on negative relative times.
Because the meteorological query is centred on the lake centroid, each lake receives a
single, spatially uniform atmospheric forcing — an approximation that is accurate for small
to medium basins but becomes a limitation at the largest fetch scales (Section 6).

### 2.4 Automated closed-lake model generation

For a closed lake — one with no open tidal or river boundaries and no point discharges —
the FLOW problem is fully determined by the grid, the time-series forcing and a small set
of physical defaults (Table 2), so the generator can assemble a complete, well-posed
configuration with no hand input. The momentum and continuity equations are integrated by
Delft3D-FLOW (Lesser et al., 2004) under the shallow-water and Boussinesq approximations on
the σ-grid, and the surface-wave field by the third-generation spectral model SWAN within
Delft3D-WAVE (Booij et al., 1999); the two run on a shared grid, so no wave-to-flow grid
interpolation is required.

The generator writes the FLOW master-definition file (`.mdf`) and its run configuration
with the following physical choices. Air–water exchange uses the Ocean heat-flux model
(Delft3D heat model 5), which resolves the short-wave, long-wave, latent and sensible
components separately from the meteorological forcing; the latent and sensible transfer are
governed by Dalton and Stanton numbers of 0.0013, and the short-wave penetration by a
prescribed Secchi depth. Vertical mixing is closed with the two-equation k–ε turbulence
model (Umlauf and Burchard, 2003). The water column is discretised into 14 σ-layers
progressively refined toward the surface, concentrating vertical resolution in the
wind-driven shear layer that controls the transport of floating material. The
evaporation–precipitation mass balance is enabled so that the free surface responds to the
net surface water flux; the Coriolis parameter is set from the true lake latitude φ as
`f = 2Ω sin φ`, capturing basin-scale rotation; and a freshwater density reference
(salinity 0) is adopted, as appropriate to inland lakes. The wave generator emits the
matching Delft3D-WAVE (SWAN) control file for a wind-forced, third-generation run with
quadruplet wave–wave interactions active, on the same counter-clockwise grid.

Because both the physical defaults and the inter-file wiring — grid names, forcing
filenames, time references and coupling intervals — are encoded in the generators rather
than entered by hand, adding a new lake requires no manual editing of model control files,
historically the most error-prone and least reproducible step in lake-model setup. The
defaults of Table 2 are exposed as parameters, so a user needing a non-default closure,
layer count or transfer coefficient can override any single value without altering the
file-generation logic.

**Table 2.** Principal physical defaults of the automated closed-lake configuration.

| Parameter | Value | Rationale |
|---|---|---|
| Vertical layers | 14 σ-layers, surface-refined | resolve surface shear for floating tracers |
| Turbulence closure | k–ε (Umlauf and Burchard, 2003) | standard two-equation closure |
| Heat flux | Ocean model (Delft3D model 5) | data-driven air–water exchange |
| Dalton / Stanton number | 0.0013 / 0.0013 | bulk latent/sensible transfer |
| Density reference | freshwater (salinity 0) | inland lakes |
| Coriolis | f from lake latitude | basin-scale rotation |
| Waves | SWAN 3rd-gen, quadruplets on | wind-sea growth |
| Open boundaries | none (closed lake) | common inland case |

### 2.5 The σ-layer → z-level coupling

This coupling is the methodological core of the pipeline, because it is the step that makes
terrain-following Delft3D output legible to a fixed-depth ocean reader. Delft3D-FLOW stores
its prognostic variables on terrain-following σ-layers: layer k is pinned to a fixed
fraction σ_{k} of the local water-column thickness, so its physical depth varies
continuously in space and time as the free surface ζ and the bed depth d evolve (Fig. 2a).
OpenDrift's generic reader, in contrast, expects every field on a single set of fixed metric
z-levels common to the whole domain (Fig. 2b). The two vertical representations are
mathematically incompatible: a σ-layer of given index does not correspond to a fixed depth,
so without an explicit reconstruction the Delft3D fields cannot be read at all. Because the
choice of vertical coordinate has a first-order effect on simulated stratification and
transport in lakes (Ishikawa et al., 2022), the reconstruction must be geometrically exact
rather than nominal. The export therefore performs four operations in a fixed order:
vertical reconstruction and regridding, velocity rotation, horizontal regridding, and
surface Stokes-drift derivation.

[[FIG:sigma_schematic]]

(1) Vertical reconstruction and regridding. For each wet cell and output time, the physical
depth of every σ-layer centre is reconstructed from the instantaneous water level ζ and the
still-water bed depth d, whose sum is the total column thickness H = ζ + d:

[[EQ:sigmaz]]

with σ_{k} = 0 at the free surface and σ_{k} = −1 at the bed. Each scalar and velocity field
is then interpolated in the vertical — by piecewise-linear interpolation in depth — from
these reconstructed σ-centre depths onto the fixed z-level set {0, −1, −2, −3, −5, −7.5, −10,
−15, −20, −30, −50} m. Two boundary treatments keep the result physically faithful: because
the shallowest σ-centre lies a finite distance below the free surface, the interpolation is
clamped to the uppermost layer value at z = 0, so that surface-trapped (floating) particles
always sample a valid velocity; and target levels lying below the local bed are masked as
missing rather than extrapolated, so that no spurious sub-bed flow is introduced (Fig. 2).
Figure 3 shows the depth-resolved result for one lake.

(2) Velocity rotation. Delft3D solves on a staggered (Arakawa C-type) curvilinear grid and
returns the velocity as grid-aligned (ξ, η) components on the cell faces. These are first
destaggered to the cell centres and then rotated from the grid axes to true geographic axes
through the local grid-orientation angle α, because OpenDrift interprets the two horizontal
components strictly as eastward and northward:

[[EQ:rotation]]

Applying the rotation per cell is essential on a curvilinear grid, where α varies across the
basin and a single global rotation would systematically misalign the currents.

(3) Horizontal regridding. The curvilinear cell centres are projected from the UTM frame
back to longitude/latitude, and the rotated fields are interpolated onto a regular
longitude–latitude raster — the only horizontal structure the generic reader accepts.
Inactive and dummy cells are masked before reprojection, so that land and padding cells
cannot distort either the interpolation or the inferred grid extent.

(4) Surface Stokes drift. The wave-driven drift is reconstructed from the SWAN output rather
than read directly. From the significant wave height H_{s}, the peak period T_{p} and the
mean propagation direction, a deep-water monochromatic approximation yields the surface
Stokes-drift magnitude (consistent with Breivik et al., 2014; van den Bremer and Breivik,
2018):

[[EQ:stokes]]

evaluated through the peak radian frequency ω = 2π/T_{p}, the deep-water wavenumber
k = ω²/g and the characteristic wave amplitude a = H_{s}/(2√2). The estimate is guarded
against the integrable singularity where the interpolated period tends to zero at the
wet/dry boundary — by imposing a minimum-period floor and a physical magnitude cap — and is
finally projected onto eastward/northward components using the mean wave direction.

The four operations yield a single CF-compliant NetCDF that carries the currents, water
level, temperature, wave parameters and surface Stokes drift on fixed z-levels in
longitude/latitude, tagged with the CF `standard_name` attributes OpenDrift recognises.
Figure 3 illustrates the depth-resolved product for one lake: the export preserves the
surface-intensified warming and the wind-driven current shear while correctly masking levels
below the bed — exactly the vertical structure that a surface-only two-dimensional forcing
would discard. Figure 4 shows the corresponding surface fields (currents, temperature and
significant wave height) for a representative lake.

[[FIG:vertical]]

[[FIG:forcing]]

### 2.6 Transport demonstration setup

To exercise the exported forcing, a thin driver seeds buoyant particles and integrates
their trajectories with OpenDrift (Dagestad et al., 2018) on the CF-NetCDF produced in
Section 2.5. Two configuration changes adapt the otherwise ocean-oriented tracker to an
inland basin. First, OpenDrift's default global coastline landmask is disabled: built for
the marine domain, it classifies the entire lake interior as land and would deactivate
every particle at the first time step. Second, a constant all-water landmask is substituted
in its place, so that stranding is governed solely by the data coverage of the forcing
itself — a particle is deactivated only when it leaves the wet region defined by the
exported fields, which is the physically correct shoreline for the modelled lake.

The release point is selected automatically and without bias toward any sub-basin. The
naive choice, the centroid of the wet cells, is unsuitable because in a non-convex basin —
the crescent-shaped Rotsee or the bent Balaton, for example — the centroid can fall on land
or in a different arm of the lake. The driver instead seeds at the lake's pole of
inaccessibility, the interior point lying farthest from any shore. This point is located as
the maximiser of the Euclidean distance transform (EDT) of the binary water mask, evaluated
with the exact linear-time algorithm of Maurer et al. (2003); the value of the transform at
that point, D_{shore}, is the distance from it to the nearest dry cell. The release radius
is then scaled to the basin so that the entire seed disk remains inside the lake at every
scale:

[[EQ:radius]]

where the cap r_{max} = 300 m bounds the radius on large lakes while the term 0.6 D_{shore}
contracts it on small ones, and particles are then drawn from a uniform distribution over
the resulting disk. Without this adaptation a fixed 300 m radius overspills small basins —
Rotsee is only ~2 km across — and seeds particles on dry ground, biasing every downstream
statistic.

The net horizontal displacement of each particle after a time t is quantified as the
distance D_{i} between its current position (λ_{i}, φ_{i}) and its release point
(λ_{0}, φ_{0}):

[[EQ:drift]]

a local equirectangular (small-angle planar) approximation to the geodesic distance on a
sphere of Earth radius R_{e} (Snyder, 1987), whose error is negligible over the
kilometre-scale separations considered here. The particle ensemble is summarised below by
the mean of D_{i} over all released particles.

---

## 3. Software description

This section describes the software that implements the methods of Section 2. We first set
out its architecture — a collection of small, independently runnable modules wired together
through standard files rather than a monolithic program (Section 3.1) — and then its
implementation, external dependencies and the minimal commands needed to stage and process
a lake (Section 3.2). The emphasis throughout is on reproducibility and reuse: each module
performs one well-defined transformation with explicit file inputs and outputs, so the
toolchain can be run end-to-end for a new lake, inspected stage by stage, or repurposed —
in particular the σ→z exporter, which can be applied on its own to any existing
Delft3D-FLOW/WAVE output.

### 3.1 Architecture and modules

The software is organised as a set of small, single-responsibility modules connected
through files rather than through shared program state, so that the data flow of Section 2
maps one-to-one onto the code (Fig. 1). Each module is an independently runnable
command-line script that reads named inputs and writes named outputs, which makes the
stages individually testable and freely re-orderable or replaceable. The modules fall into
six functional layers:

- Bathymetry ingestion — `ingest_bathy_kmz.py` (KMZ depth contours),
  `dahiti_bathymetry.py` (satellite-altimetry rasters) and `gebco_subset.py` (gridded
  bed-elevation tiles) — each emitting the common `(lon, lat, depth)` representation that
  the rest of the pipeline consumes.
- Grid construction — `build_grid.py` — projecting that point set and writing the Delft3D
  curvilinear grid triple (`.grd`, `.dep`, `.enc`).
- Meteorological forcing — the `get_era5_*.py` family — retrieving the ERA5 fields and
  writing the wind, heat-flux and evaporation–precipitation time series.
- Automated model generation — `make_flow_mdf.py` and `make_wave_mdw.py` — assembling the
  FLOW master-definition file and the WAVE/SWAN control file together with their run
  configuration.
- Coupling and transport — `cf_export.py`, which performs the σ→z reconstruction, velocity
  rotation, regridding and Stokes-drift derivation of Section 2.5, and
  `run_opendrift_demo.py`, which drives the Lagrangian demonstration on the exported
  forcing.
- Orchestration — `setup_lake.py` and `postprocess_lake.py` — chaining the per-lake stages
  on either side of the external Delft3D run.

A separate, self-contained tooling layer (`make_figures.py`, `make_equations.py`,
`build_docx.py`) regenerates every figure, the equation set and this manuscript directly
from the produced data, so that the reported results and the document itself are
reproducible artefacts of the same repository.

### 3.2 Implementation, dependencies and usage

The implementation is pure Python 3.11 and deliberately rests on a small, widely used
scientific stack: `xarray` and `netCDF4` for labelled-array and CF-NetCDF input/output,
`numpy` and `scipy` for the numerics and the distance transform, `pyproj` and `rasterio`
for projection and raster access, `cdsapi` for ERA5 retrieval, and `matplotlib` with
`cartopy` for visualisation. The Lagrangian demonstration uses OpenDrift 1.14.9; the
hydrodynamic engine, Delft3D 4.07.01 (FLOW + WAVE/SWAN), is the only heavyweight,
non-Python dependency and is installed separately — a deliberate choice to wrap, rather
than reimplement, a community-validated solver.

In normal use a lake is processed with two commands that bracket the external engine run:
`setup_lake.py` stages the grid, forcing and model-definition files from open data; the
user (or a batch script) then executes the Delft3D FLOW and WAVE runs; and
`postprocess_lake.py` performs the σ→z export and the transport demonstration. The only
per-lake inputs required are the lake location, its latitude (for the Coriolis parameter)
and a seasonal initial water temperature; an ERA5 Copernicus CDS account is needed for the
meteorological retrieval. Because the exporter depends only on the engine output and not on
how the run was configured, it can also be used on its own: pointing `cf_export.py` at the
output of any pre-existing Delft3D-FLOW/WAVE lake model converts that model's fields into
OpenDrift-ready CF-NetCDF — the component of the pipeline with the broadest independent
utility.

---

## 4. Illustrative application: twelve lakes

This section demonstrates the pipeline in practice. The aim is not to calibrate a single
waterbody but to show that one unmodified toolchain produces physically plausible forcing
across lakes that differ widely in size, depth, climate and bathymetry source. Section 4.1
describes the twelve lakes selected for this purpose and the open datasets from which each
was built; Section 4.2 specifies the common simulation and particle-release configuration
applied identically to all of them. The resulting fields and transport are analysed in
Section 5.

### 4.1 Lake selection and data sources

We applied the pipeline to twelve lakes chosen to span, as widely as practical, the
morphological and climatic factors that control lake surface transport (Fig. 5; Table 3).
The set reaches from 36°S (Lake Eucumbene, Australia) to 60°N (Lake Erken, Sweden) and so
samples all inhabited continents. Within that span it varies maximum depth by roughly an
order of magnitude — from the ~6 m of the shallow floodplain and lowland lakes to the ~80 m
of the deep peri-alpine Polyfytos basin — and surface area by more than three orders of
magnitude, and it deliberately mixes morphological types: shallow lowland and large
floodplain lakes, a deep stratifying basin, and several regulated reservoirs. It also
samples both hemispheres, so that for the Southern-Hemisphere lakes the fixed July
simulation window falls in winter rather than summer, exercising the seasonal heat forcing
in both regimes. Finally, the lakes draw on two independent bathymetry sources — digitised
survey contours and satellite-altimetry-derived DAHITI products (Schwatke et al., 2015) —
so that the demonstration tests both ingestion paths of Section 2.2. The spread is
intended to stress the generality claim directly: any single lake could be fitted by hand,
but covering this range with identical code is the property under test.

**Table 3.** The twelve demonstration lakes and key model outputs. |U|_{max} = maximum
surface current speed; H_{s} max = maximum significant wave height; drift = 36 h mean net
particle displacement.

| Lake | Country | Type | Lat | Max depth | \|U\|_{max} (m/s) | H_{s} max (m) | 36 h mean drift (m) |
|---|---|---|--:|--:|--:|--:|--:|
| Lagdo | Cameroon | tropical reservoir | 8.8 | ~9 m | 0.015 | 0.39 | 364 |
| Bornos | Spain | reservoir | 36.8 | ~20 m | 0.038 | 0.21 | 832 |
| Mead | USA | reservoir | 36.3 | ~40 m | 0.019 | 0.51 | 769 |
| Polyfytos* | Greece | reservoir | 40.2 | ~80 m | 1.18 | 0.32 | 1743 |
| Trasimeno | Italy | shallow natural | 43.1 | ~7 m | 0.012 | 0.33 | 3419 |
| Balaton | Hungary | shallow natural | 46.9 | ~9 m | 0.005 | 0.36 | 3250 |
| Rotsee | Switzerland | deep natural | 47.1 | ~16 m | 0.018 | 0.14 | 341 |
| Erken | Sweden | boreal natural | 59.8 | ~20 m | 0.010 | 0.20 | 2033 |
| Poyang | China | shallow natural | 29.1 | ~6 m | 0.020 | 0.41 | 3695 |
| Sea of Galilee | Israel | natural | 32.8 | ~6 m† | 0.032 | 0.34 | 3506 |
| Eucumbene | Australia | reservoir | −36.1 | ~38 m | 0.052 | 0.33 | 3166 |
| Nova Ponte | Brazil | reservoir | −19.1 | ~23 m | 0.030 | 0.41 | 2881 |

\*Polyfytos reuses a hand-built model that includes river discharges, hence its larger
peak currents; the other eleven are auto-generated closed-lake setups. †For Sea of
Galilee the value is the DAHITI satellite-observed depth band, not the absolute maximum
depth (Section 6).

[[FIG:map]]

### 4.2 Configuration

All twelve lakes were run with an identical configuration, so that any difference in the
results reflects the lakes themselves rather than per-lake tuning. The coupled
hydrodynamic–wave simulation covered a common two-day window in July 2022, and the only
quantities permitted to vary between lakes were the three physically necessary per-lake
inputs: the geographic location, which fixes both the grid and the meteorological query;
the latitude, which sets the Coriolis parameter; and a seasonal initial water temperature.
Eleven of the twelve models were generated fully automatically from open data by the
pipeline of Sections 2.2–2.4. The twelfth, Polyfytos, reused an existing hand-built
Delft3D-FLOW model with prescribed river discharges (Papaioannou et al., 2025) and
therefore serves as a control that isolates the export path of Section 2.5 from the
automated model-generation path — if the coupling is correct, it should produce a valid
OpenDrift forcing from a model the pipeline did not build. For the transport demonstration,
400 buoyant particles were released at the adaptive interior point of Section 2.6 in every
lake and advected for 36 h on the exported forcing, after which the net-displacement
statistic D_{i} was evaluated for each particle.

---

## 5. Results and discussion

The twelve runs are analysed below to assess whether a single unmodified pipeline yields
forcing that is internally coherent and physically ordered across the full morphological
and climatic range of the test set. We first examine the exported physical fields —
circulation, temperature and waves (Section 5.1) — then the surface transport they drive
(Section 5.2), before testing whether that transport varies with lake morphology in the
physically expected way (Section 5.3). Section 5.4 reports an automated quality-control
audit of the complete dataset and the single artefact it revealed, and Section 5.5 situates
the results relative to existing lake-modelling and transport tools. Throughout, no
parameter was tuned per lake, so the comparisons that follow are between lakes rather than
between hand-fitted models.

### 5.1 Circulation, temperature and waves

Across all twelve lakes the pipeline produces spatially coherent, wind- and heat-driven
circulation (Fig. 4, Fig. 6), even though the basins differ by an order of magnitude in
depth, by more than three orders in surface area, and span 96° of latitude (36°S to 60°N).
The wind stress organises the surface flow into basin-scale patterns — along-wind drift in
the interior with compensating return flow, and recirculating gyres in the more enclosed
basins — modulated by the shoreline geometry resolved on each grid. Surface current speeds
range from a few mm s⁻¹ in the most sheltered lakes to ~1.2 m s⁻¹ in the river-influenced
Polyfytos control (Table 3); excluding that control, the auto-generated closed lakes reach
0.5–5 cm s⁻¹, consistent with wind-driven drift currents of order a few percent of the wind
speed. The depth-resolved export (Fig. 3) shows the expected vertical structure: a
surface-intensified current that decays with depth, with a several-fold reduction in speed
between the surface and ~20 m and the strongest shear concentrated in the uppermost layers
that the σ-grid was refined to resolve (Section 2.4).

Surface temperatures track the seasonal heat forcing across both hemispheres, from 2–10 °C
in the Southern-Hemisphere winter of Lake Eucumbene to 26–35 °C in the tropical and
Mediterranean lakes, and the vertical sections (Fig. 3) reproduce surface-intensified
daytime warming and the onset of near-surface stratification rather than a vertically
uniform column. The wind-sea is fetch-limited in every basin: significant wave heights span
H_{s} = 0.14–0.51 m and scale with fetch and wind exposure, the largest waves arising on
the long-fetch reservoirs (Mead) and the smallest in the short-fetch, sheltered Rotsee —
the behaviour expected of the third-generation SWAN growth physics on enclosed water
(Section 2.4).

### 5.2 Surface transport

[[FIG:demonstration]]

Figure 6 overlays, for each lake, the time-mean surface-current field (on a per-lake colour
scale) with the 36 h trajectories of the 400 released particles and their common release
point. The trajectories remain within the basin in every case — confirming that the
all-water landmask and data-coverage stranding of Section 2.6 behave as intended — and
disperse from the compact release disk into elongated, wind-aligned plumes whose spread
reflects the spatial variability of the current field. The resulting 36 h mean net
displacement D_{i} varies over an order of magnitude, from 0.34 km in the small, deep,
sheltered Rotsee to 3.7 km in the large, shallow, fetch-exposed Poyang (Table 3). Because
every one of the twelve was processed through the same unmodified pipeline, this range is
generated by the lakes' own physics and not by any per-lake adjustment, which is the central
generalisation claim of the paper.

### 5.3 Physical consistency

[[FIG:scatter]]

Figure 7 plots the 36 h drift against lake depth and against peak current speed, isolating
the morphological controls. Two patterns emerge. First, drift decreases with depth and
increases with horizontal scale: the largest displacements occur in the large, shallow,
fetch-exposed lakes (Poyang, Sea of Galilee, Eucumbene, Trasimeno, Balaton) and the
smallest in the small, sheltered Rotsee, consistent with surface transport governed by wind
forcing and fetch, and with the morphometric controls on plastic retention identified
observationally by Nava et al. (2023) and Chen et al. (2024). Mechanistically, shallow wide
basins couple the wind stress into a thin, fast-responding surface layer with long fetch,
whereas deep basins distribute the same stress over a thicker column and a shorter relative
fetch. Second, and more diagnostically, the highest peak current — Polyfytos, driven by a
localised river inflow — does not yield the largest drift: a strong but spatially confined
jet advects particles less, in net, than a weaker but basin-wide wind drift. Net surface
transport is therefore set by basin-scale size, fetch and wind exposure rather than by peak
current magnitude. This is precisely the ordering a transport study would require the
forcing to capture, and it emerges here from open data alone, on lakes for which the
pipeline was never tuned.

### 5.4 Quality control

Two complementary checks support the integrity of the dataset. First, every exported file
was passed through an automated audit that verifies its structural and physical soundness:
monotonic coordinate axes, current and wave magnitudes within physical bounds, correctly
masked sub-bed z-levels, and a non-empty wet surface. All twelve files passed. Second, the
audit isolated a single, well-localised artefact: in the shallowest, strongly insolated
lakes (Trasimeno, Bornos, Poyang, Sea of Galilee) a few isolated near-shore cells reached
surface temperatures of up to ~40 °C, because a very thin water column over a single
solar-heated cell has negligible thermal inertia and overheats within one diurnal cycle. A
physical temperature cap of 35 °C is applied in the export to suppress these spikes, while
basin-interior temperatures — realistic throughout, for example 17–24 °C in Rotsee,
15–26 °C in Erken and 2–10 °C in the winter Eucumbene — are left unchanged. The artefact is
confined to thin-cell shorelines and does not affect the currents or waves that drive
transport; a more principled minimum-depth remedy is discussed in Section 6.

### 5.5 Relation to existing tools

It is worth stating precisely what is, and is not, new here. Relative to hand-built,
single-lake Delft3D studies (e.g. Papaioannou et al., 2025) and to inter-model comparisons
of lake hydrodynamics (Ishikawa et al., 2022), the contribution is not a new hydrodynamic
solver but the automation and coupling that turn a community-validated 3-D engine into a
push-button forcing generator for a generic particle tracker. Relative to site-specific
transport frameworks such as CaMPSim-3D (Pilechi et al., 2022), which couple a particle
model to one particular hydrodynamic engine on a per-study basis, LakeForcing-OpenDrift
instead targets a generic CF reader: the same exported forcing can drive OpenDrift or
Parcels (Delandmeter and van Sebille, 2019) without change, and the same workflow applies
to any lake. Of the pipeline's parts, the σ→z export has the broadest independent reach,
since it is independent of run configuration and can make any existing Delft3D-FLOW/WAVE
lake model OpenDrift-ready by being pointed at its output. Finally, we are explicit about
scope: the present results establish physical plausibility and internal consistency across a
wide range of lakes rather than validation against in-situ drifter or tracer observations.
Such quantitative, per-lake validation is the natural next step, and it is enabled — not
foreclosed — by releasing the forcing openly.

---

## 6. Limitations and future work

Several limitations bound the present implementation, most of them deliberate
simplifications that trade physical completeness for automation and generality. The most
consequential concerns the atmospheric forcing. Each lake is driven by a single ERA5 column
sampled at its centroid, so the wind, heat and mass-balance forcing is spatially uniform
over the basin. For the small and medium lakes that dominate the global inventory this is
an acceptable approximation, because the basin is far smaller than the synoptic scale on
which the wind varies; but on the largest lakes — at the scale of the Laurentian Great
Lakes or the Caspian Sea — spatial wind gradients drive an appreciable part of the
circulation, and a single column cannot represent them. The same reanalysis also sets a
resolution floor: ERA5's native ~31 km grid (or the ~9 km high-resolution sub-set)
under-resolves the near-shore wind and the lake–land breeze, smoothing precisely the
gradients that matter most along the shoreline where floating material tends to accumulate.
Both limitations are addressable within the existing file interface, by ingesting a
spatially distributed wind field in place of a point time series.

A second group of limitations concerns the wave field. For computational economy the
demonstration uses a stationary SWAN solution — the wave field is computed for
representative wind states rather than continuously coupled in time — which is adequate for
the slowly varying wind-seas of enclosed lakes but cannot capture the transient growth and
decay of waves under a rapidly veering storm; a fully time-varying wave run is supported by
the same generator at greater cost. The surface Stokes drift is, in turn, reconstructed
from bulk wave parameters through a deep-water, monochromatic approximation (Section 2.5),
which reproduces the magnitude and direction of the surface drift but not its vertical
decay; for deeply submerged or weakly buoyant tracers a spectral or depth-resolved Stokes
profile (Breivik et al., 2014; van den Bremer and Breivik, 2018) would represent the
near-surface shear more faithfully.

Two further limitations stem from the input data and the physical configuration. Where
bathymetry is derived from satellite altimetry, the DAHITI product captures the depth band
the altimeter has observed over its mission, which need not coincide with the absolute
maximum depth of the basin; the resulting grid is therefore conservative in the deepest,
least-sampled parts of such lakes, the Sea of Galilee being the clearest case here. And
because inland lakes are modelled with a freshwater density reference and no active salinity
transport, the configuration does not apply as-is to hypersaline or strongly saline
waterbodies such as the Dead Sea, which would require the salinity transport and a
corresponding equation of state to be enabled — both available in Delft3D, but switched off
by default in the automated closed-lake setup. A final, localised numerical artefact,
already noted in Section 5.4, bears restating here: in very thin near-shore cells under
strong insolation the negligible thermal inertia of a one-cell-deep column can produce
unphysical surface-temperature spikes. The export suppresses these with a 35 °C cap and
they affect neither the currents nor the waves that drive transport, but a more principled
remedy — a minimum-depth (wetting–drying) threshold that removes such cells before they
overheat — is preferable and is planned.

Together these limitations define a clear development path. Future work will introduce
spatially distributed wind for large lakes, time-varying wave forcing, an explicit salinity
and temperature equation of state for saline systems, a minimum-depth treatment for thin
shoreline cells, and a depth-dependent Stokes profile. Beyond these refinements, the
natural next step is quantitative validation against in-situ drifter or tracer observations
for individual lakes (Section 5.5) and, at scale, application of the workflow to a
HydroLAKES sub-sample (Messager et al., 2016; Lehner and Döll, 2004) to build a standing,
openly distributed archive of lake forcing for community reuse.

---

## 7. Conclusions

We have presented LakeForcing-OpenDrift, an open and reproducible pipeline that converts
open global data — HydroLAKES, GLOBathy and DAHITI bathymetry together with ERA5
meteorology — into hydrodynamic and wind-wave forcing for an arbitrary inland lake, and
delivers it as CF-compliant NetCDF that drives the OpenDrift particle tracker without
modification. Its methodological core is a fully specified σ-layer to z-level coupling
which, together with the curvilinear-to-geographic velocity rotation, the horizontal
regridding and the surface Stokes-drift derivation, resolves the vertical-coordinate
mismatch that otherwise prevents terrain-following Delft3D output from being read by a
generic ocean tracker. Combined with the automated generation of closed-lake Delft3D
models, this turns a community-validated three-dimensional engine into a push-button forcing
generator and removes the per-lake bottleneck that has kept Lagrangian transport modelling
out of reach for most inland waters.

Demonstrated unchanged across twelve morphologically and climatically diverse lakes
spanning all inhabited continents (36°S–60°N), the pipeline yields physically coherent and
internally consistent forcing in every case. The surface circulation organises into
basin-scale, wind-driven patterns with realistic vertical shear; surface temperatures track
the seasonal heat forcing across both hemispheres, from 2–10 °C in the Southern-Hemisphere
winter to 26–35 °C in the tropical and Mediterranean lakes; and the fetch-limited wind-sea
produces significant wave heights of H_{s} = 0.14–0.51 m that scale correctly with fetch
and exposure. The 36-h surface drift spans an order of magnitude, from 0.34 km in the
small, deep, sheltered Rotsee to 3.7 km in the large, shallow, fetch-exposed Poyang, and is
ordered by basin size, fetch and wind exposure rather than by peak current — tellingly, the
river-driven Polyfytos, which carries the strongest local current, does not produce the
largest drift. This ordering reproduces, from open data and without any per-lake tuning, the
morphometric controls on surface retention reported observationally for lake plastics (Nava
et al., 2023; Chen et al., 2024), and an automated audit confirmed the structural and
physical integrity of all twelve exported datasets.

By removing the forcing bottleneck and releasing the complete toolchain and the twelve-lake
forcing dataset under permissive licences, the work lowers the barrier to lake-scale studies
of plastics, oil spills, harmful algal blooms and ecological transport, and provides a
reusable bridge — the σ→z exporter — that can make any existing Delft3D lake model
OpenDrift-ready. The present results establish physical plausibility and generality rather
than per-lake validation; coupling the openly released forcing to in-situ observations, and
scaling the workflow toward a global, HydroLAKES-wide forcing archive, are the natural next
steps.

---

## Software availability

| | |
|---|---|
| Software name | LakeForcing-OpenDrift |
| Version | v1.0.1 |
| Developers | V. Papaioannou, C. Anagnostopoulos, A. Moumtzidou, I. Gialampoukidis, S. Vrochidis, I. Kompatsiaris (CERTH-ITI) |
| Contact | Vassilios Papaioannou — vaspapa@iti.gr; CERTH-ITI, 6th km Charilaou-Thermi, 57001 Thessaloniki, Greece |
| Year first available | 2025 |
| Programming language | Python 3.11 |
| Software dependencies | xarray, numpy, scipy, pyproj, rasterio, netCDF4, cdsapi, matplotlib, cartopy; OpenDrift 1.14.9 |
| External hydrodynamic engine | Delft3D 4.07.01 (FLOW + WAVE/SWAN), installed separately |
| External data services | ERA5 (Copernicus CDS account required); HydroLAKES; GLOBathy; DAHITI |
| Operating systems | Windows and Linux (64-bit) |
| Hardware requirements | Standard workstation; a multi-core CPU is recommended for the Delft3D-FLOW/WAVE runs |
| Source-code size | approximately 0.2 MB (excluding generated data) |
| Documentation | Repository README and the present manuscript |
| Source repository | https://github.com/vaspapa79/LakeForcing-OpenDrift |
| Permanent archive | Zenodo, citable DOI minted at acceptance |
| Licence | MIT (source code); CC-BY-4.0 (generated forcing dataset) |
| Availability and cost | Free and open source |

## CRediT authorship contribution statement
**V.P.:** Conceptualization, Methodology, Software, Validation, Writing – original draft.
**C.A.:** Software, Validation, Writing – review & editing. **A.M.:** Data curation,
Writing – review & editing. **I.G.:** Methodology, Writing – review & editing. **S.V.:**
Supervision, Writing – review & editing. **I.K.:** Supervision, Funding acquisition.

## Declaration of competing interest
The authors declare that they have no known competing financial interests or personal
relationships that could have appeared to influence the work reported in this paper.

## Data availability
The source code is openly available at https://github.com/vaspapa79/LakeForcing-OpenDrift
under the MIT licence and is archived on Zenodo with a citable DOI (DOI to be inserted at
acceptance). The generated twelve-lake forcing dataset (CC-BY-4.0) and the full
reproducibility data are distributed as release assets of the same repository. All input
datasets (HydroLAKES, GLOBathy, DAHITI, ERA5) are openly available from their respective
providers.

## Funding
This research did not receive any specific grant from funding agencies in the public,
commercial, or not-for-profit sectors. The work was carried out using the existing research
infrastructure of the Information Technologies Institute, Centre for Research and Technology
Hellas (CERTH-ITI).

## Acknowledgements
The authors thank the developers of Delft3D (Deltares) and OpenDrift, and the providers of
the open datasets used here (HydroLAKES, GLOBathy, DAHITI and ERA5).

## References

Alduchov, O.A., Eskridge, R.E., 1996. Improved Magnus form approximation of saturation vapor pressure. *J. Appl. Meteorol.* 35, 601–609. https://doi.org/10.1175/1520-0450(1996)035<0601:IMFAOS>2.0.CO;2

Booij, N., Ris, R.C., Holthuijsen, L.H., 1999. A third-generation wave model for coastal regions: 1. Model description and validation. *J. Geophys. Res. Oceans* 104(C4), 7649–7666. https://doi.org/10.1029/98JC02622

Breivik, Ø., Janssen, P.A.E.M., Bidlot, J.-R., 2014. Approximate Stokes drift profiles in deep water. *J. Phys. Oceanogr.* 44, 2433–2445. https://doi.org/10.1175/JPO-D-14-0020.1

Chen, D., Wang, P., Liu, S., Wang, R., Wu, Y., Zhu, A.-X., Deng, C., 2024. Global patterns of lake microplastic pollution: insights from regional human development levels. *Sci. Total Environ.* 954, 176620. https://doi.org/10.1016/j.scitotenv.2024.176620

Cózar, A., Echevarría, F., González-Gordillo, J.I., Irigoien, X., Úbeda, B., Hernández-León, S., Palma, Á.T., Navarro, S., García-de-Lomas, J., Ruiz, A., Fernández-de-Puelles, M.L., Duarte, C.M., 2014. Plastic debris in the open ocean. *Proc. Natl. Acad. Sci. USA* 111, 10239–10244. https://doi.org/10.1073/pnas.1314705111

Dagestad, K.-F., Röhrs, J., Breivik, Ø., Ådlandsvik, B., 2018. OpenDrift v1.0: a generic framework for trajectory modelling. *Geosci. Model Dev.* 11, 1405–1420. https://doi.org/10.5194/gmd-11-1405-2018

Delandmeter, P., van Sebille, E., 2019. The Parcels v2.0 Lagrangian framework: new field interpolation schemes. *Geosci. Model Dev.* 12, 3571–3584. https://doi.org/10.5194/gmd-12-3571-2019

Hersbach, H., Bell, B., Berrisford, P., Hirahara, S., Horányi, A., Muñoz-Sabater, J., Nicolas, J., Peubey, C., Radu, R., Schepers, D., Simmons, A., Soci, C., Abdalla, S., Abellan, X., Balsamo, G., Bechtold, P., Biavati, G., Bidlot, J., Bonavita, M., De Chiara, G., Dahlgren, P., Dee, D., Diamantakis, M., Dragani, R., Flemming, J., Forbes, R., Fuentes, M., Geer, A., Haimberger, L., Healy, S., Hogan, R.J., Hólm, E., Janisková, M., Keeley, S., Laloyaux, P., Lopez, P., Lupu, C., Radnoti, G., de Rosnay, P., Rozum, I., Vamborg, F., Villaume, S., Thépaut, J.-N., 2020. The ERA5 global reanalysis. *Q. J. R. Meteorol. Soc.* 146, 1999–2049. https://doi.org/10.1002/qj.3803

Hipsey, M.R., Bruce, L.C., Boon, C., Busch, B., Carey, C.C., Hamilton, D.P., Hanson, P.C., Read, J.S., de Sousa, E., Weber, M., Winslow, L.A., 2019. A General Lake Model (GLM 3.0) for linking with high-frequency sensor data. *Geosci. Model Dev.* 12, 473–523. https://doi.org/10.5194/gmd-12-473-2019

Ishikawa, M., Gonzalez, W., Golyjeswski, O., Sales, G., Rigotti, J.A., Bleninger, T., Mannich, M., Lorke, A., 2022. Effects of dimensionality on the performance of hydrodynamic models for stratified lakes and reservoirs. *Geosci. Model Dev.* 15, 2197–2220. https://doi.org/10.5194/gmd-15-2197-2022

Khazaei, B., Read, L.K., Casali, M., Sampson, K.M., Yates, D.N., 2022. GLOBathy, the global lakes bathymetry dataset. *Sci. Data* 9, 36. https://doi.org/10.1038/s41597-022-01132-9

Kukulka, T., Proskurowski, G., Morét-Ferguson, S., Meyer, D.W., Law, K.L., 2012. The effect of wind mixing on the vertical distribution of buoyant plastic debris. *Geophys. Res. Lett.* 39, L07601. https://doi.org/10.1029/2012GL051116

Lehner, B., Döll, P., 2004. Development and validation of a global database of lakes, reservoirs and wetlands. *J. Hydrol.* 296, 1–22. https://doi.org/10.1016/j.jhydrol.2004.03.028

Lesser, G., Roelvink, J., van Kester, J., Stelling, G., 2004. Development and validation of a three-dimensional morphological model. *Coastal Eng.* 51, 883–915. https://doi.org/10.1016/j.coastaleng.2004.07.014

Maurer, C., Rensheng Qi, Raghavan, V., 2003. A linear time algorithm for computing exact Euclidean distance transforms of binary images in arbitrary dimensions. *IEEE Trans. Pattern Anal. Mach. Intell.* 25, 265–270. https://doi.org/10.1109/TPAMI.2003.1177156

Messager, M.L., Lehner, B., Grill, G., Nedeva, I., Schmitt, O., 2016. Estimating the volume and age of water stored in global lakes (HydroLAKES). *Nat. Commun.* 7, 13603. https://doi.org/10.1038/ncomms13603

Nava, V., Chandra, S., Aherne, J., Alfonso, M.B., Antão-Geraldes, A.M., Attermeyer, K., Bao, R., Bartrons, M., Berger, S.A., Biernaczyk, M., Bissen, R., Brookes, J.D., Brown, D., Cañedo-Argüelles, M., Canle, M., Capelli, C., Carballeira, R., Cereijo, J.L., Chawchai, S., Christensen, S.T., Christoffersen, K.S., de Eyto, E., Delgado, J., Dornan, T.N., Doubek, J.P., Dusaucy, J., Erina, O., Ersoy, Z., Feuchtmayr, H., Frezzotti, M.L., Galafassi, S., Gateuille, D., Gonçalves, V., Grossart, H.-P., Hamilton, D.P., Harris, T.D., Kangur, K., Kankılıç, G.B., Kessler, R., Kiel, C., Krynak, E.M., Leiva-Presa, À., Lepori, F., Matias, M.G., Matsuzaki, S.-I.S., McElarney, Y., Messyasz, B., Mitchell, M., Mlambo, M.C., Motitsoe, S.N., Nandini, S., Orlandi, V., Owens, C., Özkundakci, D., Pinnow, S., Pociecha, A., Raposeiro, P.M., Rõõm, E.-I., Rotta, F., Salmaso, N., Sarma, S.S.S., Sartirana, D., Scordo, F., Sibomana, C., Siewert, D., Stepanowska, K., Tavşanoğlu, Ü.N., Tereshina, M., Thompson, J., Tolotti, M., Valois, A., Verburg, P., Welsh, B., Wesolek, B., Weyhenmeyer, G.A., Wu, N., Zawisza, E., Zink, L., Leoni, B., 2023. Plastic debris in lakes and reservoirs. *Nature* 619, 317–322. https://doi.org/10.1038/s41586-023-06168-4

Onink, V., Wichmann, D., Delandmeter, P., van Sebille, E., 2019. The role of Ekman currents, geostrophy, and Stokes drift in the accumulation of floating microplastic. *J. Geophys. Res. Oceans* 124, 1474–1490. https://doi.org/10.1029/2018JC014547

Papaioannou, V., Mantsis, D.F., Anagnostopoulos, C.G., Vlachos, K., Moumtzidou, A., Gialampoukidis, I., Vrochidis, S., Kompatsiaris, I., 2025. Integrated hydrodynamic and atmospheric modelling of Polyfytos Lake for substance dispersion using Delft3D and WRF. *Open J. Civ. Eng.* https://doi.org/10.4236/ojce.2025.152013

Pilechi, A., Mohammadian, A., Murphy, E., 2022. A numerical framework for modeling fate and transport of microplastics in inland and coastal waters (CaMPSim-3D). *Mar. Pollut. Bull.* 184, 114119. https://doi.org/10.1016/j.marpolbul.2022.114119

Schwatke, C., Dettmering, D., Bosch, W., Seitz, F., 2015. DAHITI – an innovative approach for estimating water level time series over inland waters using multi-mission satellite altimetry. *Hydrol. Earth Syst. Sci.* 19, 4345–4364. https://doi.org/10.5194/hess-19-4345-2015

Snyder, J.P., 1987. Map Projections — A Working Manual. *U.S. Geological Survey Professional Paper* 1395. U.S. Government Printing Office, Washington, D.C. https://doi.org/10.3133/pp1395

Umlauf, L., Burchard, H., 2003. A generic length-scale equation for geophysical turbulence models. *J. Mar. Res.* 61, 235–265. https://doi.org/10.1357/002224003322005087

van den Bremer, T.S., Breivik, Ø., 2018. Stokes drift. *Phil. Trans. R. Soc. A* 376, 20170104. https://doi.org/10.1098/rsta.2017.0104

van Sebille, E., Aliani, S., Law, K.L., Maximenko, N., Alsina, J.M., Bagaev, A., Bergmann, M., Chapron, B., Chubarenko, I., Cózar, A., Delandmeter, P., Egger, M., Fox-Kemper, B., Garaba, S.P., Goddijn-Murphy, L., Hardesty, B.D., Hoffman, M.J., Isobe, A., Jongedijk, C.E., Kaandorp, M.L.A., Khatmullina, L., Koelmans, A.A., Kukulka, T., Laufkötter, C., Lebreton, L., Lobelle, D., Maes, C., Martinez-Vicente, V., Morales Maqueda, M.A., Poulain-Zarcos, M., Rodríguez, E., Ryan, P.G., Shanks, A.L., Shim, W.J., Suaria, G., Thiel, M., van den Bremer, T.S., Wichmann, D., 2020. The physical oceanography of the transport of floating marine debris. *Environ. Res. Lett.* 15, 023003. https://doi.org/10.1088/1748-9326/ab6d7d

Wagner, M., Scherer, C., Alvarez-Muñoz, D., Brennholt, N., Bourrain, X., Buchinger, S., Fries, E., Grosbois, C., Klasmeier, J., Marti, T., Rodriguez-Mozaz, S., Urbatzka, R., Vethaak, A.D., Winther-Nielsen, M., Reifferscheid, G., 2014. Microplastics in freshwater ecosystems: what we know and what we need to know. *Environ. Sci. Eur.* 26, 12. https://doi.org/10.1186/s12302-014-0012-7

Wüest, A., Lorke, A., 2003. Small-scale hydrodynamics in lakes. *Annu. Rev. Fluid Mech.* 35, 373–412. https://doi.org/10.1146/annurev.fluid.35.101101.161220
