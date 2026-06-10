# Setup & run notes (Polyfytos prototype)

You run Delft3D yourself — these are the inputs/sequence so the outputs slot
straight into the export. **Nothing here runs automatically.**

## 0. One change needed for FLOW output to be readable

`cf_export.py` reads a **NetCDF** map file (`trim-*.nc`). By default Delft3D-FLOW
writes NEFIS (`trim-*.dat/.def`). Two options:

- **Preferred** — add this line to `polifitos.mdf` and run FLOW once more:
  ```
  FlNcdf = #map his#
  ```
  This makes FLOW write `trim-polifitos.nc` directly.
- **Or** keep your current NEFIS output and convert afterwards (NEFIS→NetCDF via
  the Delft3D MATLAB toolbox `vs_*` / `qpread`, or `nefis2nc`). Tell me and I'll
  wire the conversion into step 6 instead.

The σ→z transform in `cf_export.py` needs the sigma layer-centre coordinates
(`SIG_LYR`), water level (`S1`), bed depth (`DPS`) and the grid angle (`ALFAS`) —
all present in the standard trim output.

## 1. Currents / temperature / level  (FLOW — already yours)

Your existing `polifitos.mdf` run already produces these. Just ensure NetCDF
output per step 0. No other change.

## 2. Waves  (WAVE/SWAN — new, when you're ready)

Generate the `.mdw` (writes input only):
```
conda run -n plastic python src/make_wave_mdw.py ^
  --grid "C:/Users/vaspapa/Desktop/Greek_lakes/Lake Polyfytos/polifitos.grd" ^
  --out  "C:/Users/vaspapa/Desktop/Greek_lakes/Lake Polyfytos/polifitos.mdw" ^
  --name polyfytos --refdate 2022-07-01 --wind-speed 7 --wind-dir 320
```
Then **you** launch it (I will not):
```
"C:/Program Files/Deltares/Delft3D 4.07.01/kernels/x64/bin/run_dwaves.bat" polifitos.mdw
```
→ produces `wavm-polifitos.nc` (Hs, Tp, direction) on the same grid.

> The `--wind-speed/--wind-dir` here are a single uniform state for a first
> stationary test. For the published dataset we'll drive SWAN with the ERA5 wind
> time series (multiple `[TimePoint]` blocks) so waves co-vary with the currents.

## 3. Export → CF-NetCDF  (σ→z fix; no Delft3D needed)

```
conda run -n plastic python src/cf_export.py ^
  --flow "C:/Users/vaspapa/Desktop/Greek_lakes/Lake Polyfytos/trim-polifitos.nc" ^
  --wave "C:/Users/vaspapa/Desktop/Greek_lakes/Lake Polyfytos/wavm-polifitos.nc" ^
  --src-crs EPSG:32634 --lake polyfytos ^
  --out output/polyfytos_forcing.nc
```

## 4. Validate with OpenDrift  (no Delft3D needed)

```
conda run --no-capture-output -n plastic python src/run_opendrift_demo.py ^
  --forcing output/polyfytos_forcing.nc --lon 21.95 --lat 40.20
```
Check the reader printout lists `depth` in metres (0…−50) and that particles move.

## Verify-once items (against the first real trim-*.nc)
- `SIG_LYR` sign (0→−1 vs 0→1) — auto-handled but confirm.
- `U1`/`V1` staggering direction (which axis is M/xi).
- WAVE var names `HSIGN`/`RTP`/`DIR`.
These are the only model-build-specific bits; everything else is generic.
