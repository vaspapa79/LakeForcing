"""
postprocess_lake.py -- after FLOW+WAVE, finish one lake: cf_export (sigma->z CF
NetCDF) -> OpenDrift demo (at a verified-wet seed) -> demo plot. No Delft3D.

Usage:
  python src/postprocess_lake.py --prefix balaton [--hours 36 --n 400]
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
PY = sys.executable


def run(*cmd):
    cmd = [str(c) for c in cmd]
    r = subprocess.run([PY, *cmd], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stderr or "")[-500:])
        raise SystemExit(f"failed: {cmd[1]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--hours", type=int, default=36)
    ap.add_argument("--n", type=int, default=400)
    a = ap.parse_args()
    p = a.prefix
    d = ROOT / "models" / p
    epsg = json.loads((d / f"{p}_grid.json").read_text())["epsg"]
    trim, wavm = d / f"trim-{p}.nc", d / f"wavm-{p}.nc"
    if not trim.exists():
        raise SystemExit(f"{p}: no trim (FLOW not done)")
    forcing = ROOT / "output" / f"{p}_forcing.nc"

    print(f"[{p}] cf_export (src EPSG:{epsg}) ...")
    args = ["src/cf_export.py", "--flow", trim, "--src-crs", f"EPSG:{epsg}",
            "--lake", p, "--out", forcing]
    if wavm.exists():
        args += ["--wave", wavm]
    run(*args)

    # verified-wet seed (finite surface current)
    import xarray as xr
    from scipy import ndimage
    ds = xr.open_dataset(forcing)
    u0 = ds["u"].isel(time=0, depth=0).values
    wet = np.isfinite(u0)
    LON, LAT = np.meshgrid(ds.lon.values, ds.lat.values)
    # Robust interior release point: the wet cell farthest from any shore
    # (the lake's "pole of inaccessibility"). The plain wet-cell centroid can
    # fall on dry ground for non-convex lakes (crescent-shaped Rotsee, bent
    # Balaton), so we use the distance transform of the wet mask instead.
    dist = ndimage.distance_transform_edt(wet)
    ji = np.unravel_index(np.argmax(dist), dist.shape)
    lon0, lat0 = float(LON[ji]), float(LAT[ji])
    # Adaptive release radius: keep the whole seed disk inside the basin by
    # taking a fraction of the release point's distance to the nearest shore.
    # A fixed radius (e.g. 300 m) overspills small lakes such as Rotsee
    # (~2 km across) and seeds particles on land.
    coslat = np.cos(np.deg2rad(lat0))
    cell_m = abs(float(np.median(np.diff(ds.lon.values)))) * coslat * 111e3
    shore_m = float(dist.max()) * cell_m
    radius = float(min(300.0, 0.6 * shore_m))
    print(f"[{p}] {int(wet.sum())} surface wet cells; seed {lon0:.4f},{lat0:.4f} "
          f"radius {radius:.0f} m (shore dist {shore_m:.0f} m)")
    # sidecar so the demonstration figure marks the true release centre
    (ROOT / "output" / f"{p}_seed.json").write_text(
        json.dumps({"lon": lon0, "lat": lat0, "radius": radius}))

    traj = ROOT / "output" / f"{p}_trajectory.nc"
    print(f"[{p}] OpenDrift ...")
    run("src/run_opendrift_demo.py", "--forcing", forcing, "--lon", lon0,
        "--lat", lat0, "--radius", radius, "--hours", a.hours, "--n", a.n,
        "--out", traj)

    # quick drift stat
    t = xr.open_dataset(traj); lon, lat = t["lon"].values, t["lat"].values
    dd = np.sqrt(((lon[:, -1] - lon[:, 0]) * np.cos(np.deg2rad(lat0)) * 111e3) ** 2
                 + ((lat[:, -1] - lat[:, 0]) * 111e3) ** 2)
    dd = dd[np.isfinite(dd)]
    print(f"[{p}] DONE: {lon.shape[0]} particles, mean drift {dd.mean():.0f} m, "
          f"max {dd.max():.0f} m")


if __name__ == "__main__":
    main()
