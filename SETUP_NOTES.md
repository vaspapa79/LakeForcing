# Applying the σ-to-z exporter to an existing Delft3D model

The σ-to-z exporter (`cf_export.py`) is independent of how a Delft3D model was built, so it
can be pointed at the output of any existing Delft3D-FLOW/WAVE lake model to produce
OpenDrift-ready CF-NetCDF. This note documents the inputs and the sequence; the heavyweight
Delft3D-FLOW/WAVE runs are performed by the user with their own engine installation.

## 1. Make the FLOW output NetCDF-readable

`cf_export.py` reads a **NetCDF** map file (`trim-*.nc`). By default Delft3D-FLOW writes
NEFIS (`trim-*.dat` / `.def`). Either:

- **Preferred** — add the following line to the model's `.mdf` and run FLOW once more, so
  FLOW writes `trim-<name>.nc` directly:
  ```
  FlNcdf = #map his#
  ```
- **Or** keep NEFIS output and convert afterwards (NEFIS→NetCDF via the Delft3D MATLAB
  toolbox `vs_*` / `qpread`, or `nefis2nc`).

The σ-to-z transform needs the σ layer-centre coordinates (`SIG_LYR`), the water level
(`S1`), the bed depth (`DPS`) and the grid angle (`ALFAS`) — all present in the standard
trim output.

## 2. Currents, temperature and water level (FLOW)

An existing `.mdf` run already produces these; only the NetCDF output of step 1 is required.

## 3. Waves (WAVE / SWAN)

Generate the `.mdw` (writes input only):
```
python src/make_wave_mdw.py \
  --grid  path/to/<name>.grd \
  --out   path/to/<name>.mdw \
  --name  <name> --refdate 2022-07-01 --wind-speed 7 --wind-dir 320
```
then launch the WAVE run with the Delft3D engine:
```
run_dwaves.bat <name>.mdw
```
which produces `wavm-<name>.nc` (significant wave height, peak period, mean direction) on
the same grid.

> `--wind-speed` / `--wind-dir` specify a single stationary wind state. For a
> time-varying wave field, the generator also accepts multiple `[TimePoint]` blocks driven
> by the ERA5 wind time series, so that waves co-vary with the currents (Section 6 of the
> manuscript).

## 4. Export to CF-NetCDF (σ-to-z; no Delft3D required)
```
python src/cf_export.py \
  --flow path/to/trim-<name>.nc \
  --wave path/to/wavm-<name>.nc \
  --src-crs EPSG:<utm-zone> --lake <name> \
  --out output/<name>_forcing.nc
```

## 5. Drive OpenDrift (no Delft3D required)
```
python src/run_opendrift_demo.py \
  --forcing output/<name>_forcing.nc --lon <lon> --lat <lat>
```
Confirm the reader printout lists `depth` in metres (0…−50 m) and that particles advect.

## Model-build-specific checks (verify once against the first real trim-*.nc)
- `SIG_LYR` sign convention (0→−1 vs 0→1) — auto-detected; confirm.
- `U1` / `V1` staggering direction (which axis is the M/ξ axis).
- WAVE variable names (`HSIGN` / `RTP` / `DIR`).

Everything else in the exporter is generic and model-independent.
