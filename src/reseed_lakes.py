"""
reseed_lakes.py -- re-run only the OpenDrift transport demo for every lake using
the corrected release scheme (robust interior seed + adaptive, hard-bounded
radius), reusing the existing QC'd *_forcing.nc. Does NOT touch Delft3D or
cf_export. Writes <lake>_seed.json, regenerates <lake>_trajectory.nc, and prints
updated drift statistics for Table 1.

Run with the OpenDrift env:
  C:/Users/vaspapa/miniconda3/envs/plastic/python.exe src/reseed_lakes.py
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
import xarray as xr
from scipy import ndimage

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
OUT = ROOT / "output"
PY = sys.executable
LAKES = ["lagdo", "trasimeno", "balaton", "bornos",
         "mead", "polyfytos", "rotsee", "erken"]
HOURS, N = 36, 400


def seed_for(forcing):
    ds = xr.open_dataset(forcing)
    u0 = ds["u"].isel(time=0, depth=0).values
    wet = np.isfinite(u0)
    LON, LAT = np.meshgrid(ds.lon.values, ds.lat.values)
    dist = ndimage.distance_transform_edt(wet)
    ji = np.unravel_index(np.argmax(dist), dist.shape)
    lon0, lat0 = float(LON[ji]), float(LAT[ji])
    coslat = np.cos(np.deg2rad(lat0))
    cell_m = abs(float(np.median(np.diff(ds.lon.values)))) * coslat * 111e3
    shore_m = float(dist.max()) * cell_m
    radius = float(min(300.0, 0.6 * shore_m))
    return lon0, lat0, radius, shore_m, int(wet.sum()), wet, LON, LAT


def main():
    rows = []
    for p in LAKES:
        forcing = OUT / f"{p}_forcing.nc"
        if not forcing.exists():
            print(f"[{p}] no forcing, skip"); continue
        lon0, lat0, radius, shore_m, nwet, wet, LON, LAT = seed_for(forcing)
        (OUT / f"{p}_seed.json").write_text(
            json.dumps({"lon": lon0, "lat": lat0, "radius": radius}))
        print(f"[{p}] {nwet} wet cells; seed {lon0:.4f},{lat0:.4f} "
              f"radius {radius:.0f} m (shore {shore_m:.0f} m)")
        traj = OUT / f"{p}_trajectory.nc"
        r = subprocess.run(
            [PY, str(ROOT / "src/run_opendrift_demo.py"),
             "--forcing", str(forcing), "--lon", str(lon0), "--lat", str(lat0),
             "--radius", str(radius), "--hours", str(HOURS), "--n", str(N),
             "--out", str(traj)],
            cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            print((r.stderr or "")[-800:]); print(f"[{p}] FAILED"); continue
        t = xr.open_dataset(traj)
        lon, lat = t["lon"].values, t["lat"].values
        # fraction of initial particles on a dry cell (should be ~0 now)
        def iswet(lo, la):
            j = np.unravel_index(np.argmin((LON - lo) ** 2 + (LAT - la) ** 2), LON.shape)
            return wet[j]
        dry0 = sum(0 if iswet(lo, la) else 1 for lo, la in zip(lon[:, 0], lat[:, 0]))
        dd = np.sqrt(((lon[:, -1] - lon[:, 0]) * np.cos(np.deg2rad(lat0)) * 111e3) ** 2
                     + ((lat[:, -1] - lat[:, 0]) * 111e3) ** 2)
        dd = dd[np.isfinite(dd)]
        rows.append((p, lon.shape[0], dd.mean(), dd.max(), dry0, N))
        print(f"[{p}] DONE drift mean {dd.mean():.0f} m max {dd.max():.0f} m; "
              f"initial-dry {dry0}/{N}")
    print("\n=== updated drift table ===")
    print(f"{'lake':11s} {'N':>4s} {'mean_m':>7s} {'max_m':>7s} {'dry0':>6s}")
    for p, n, m, mx, d0, ntot in rows:
        print(f"{p:11s} {n:4d} {m:7.0f} {mx:7.0f} {d0:4d}/{ntot}")


if __name__ == "__main__":
    main()
