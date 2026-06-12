"""
batch_windage.py -- re-export each lake's forcing WITH the 10 m wind, then run the
OpenDrift demo twice: current+Stokes (wind_drift_factor=0, the canonical trajectory)
and +2% windage (0.02). Records both mean/max drifts to output/wind_drift_stats.json.

Run in the plastic env:
  conda run -n plastic python src/batch_windage.py
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
import xarray as xr
from scipy import ndimage

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
PY = sys.executable
LAKES = ["lagdo", "bornos", "mead", "polyfytos", "trasimeno", "balaton",
         "rotsee", "erken", "poyang", "sea_of_galilee", "eucumbene", "nova_ponte"]

# Hand-built models use non-standard filenames / no grid.json.
OVERRIDES = {
    "polyfytos": dict(epsg=32634, trim="trim-polifitos.nc",
                      wavm="wavm-polifitos.nc", wnd="polifitos.wnd"),
}


def run(*cmd):
    r = subprocess.run([PY, *map(str, cmd)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stderr or "")[-800:])
        raise SystemExit(f"failed: {cmd[1]}")
    return r.stdout


def drift_stats(traj, lat0):
    t = xr.open_dataset(traj)
    lon, lat = t["lon"].values, t["lat"].values
    dd = np.sqrt(((lon[:, -1] - lon[:, 0]) * np.cos(np.deg2rad(lat0)) * 111e3) ** 2
                 + ((lat[:, -1] - lat[:, 0]) * 111e3) ** 2)
    dd = dd[np.isfinite(dd)]
    t.close()
    return float(dd.mean()), float(dd.max())


def main():
    statf = ROOT / "output" / "wind_drift_stats.json"
    stats = json.loads(statf.read_text()) if statf.exists() else {}
    for p in LAKES:
        d = ROOT / "models" / p
        tr0 = ROOT / "output" / f"{p}_trajectory.nc"
        trw = ROOT / "output" / f"{p}_trajectory_wind.nc"
        forcing = ROOT / "output" / f"{p}_forcing.nc"
        # resume: if both demos already exist, just (re)compute stats and skip
        if tr0.exists() and trw.exists() and (ROOT / "output" / f"{p}_seed.json").exists():
            lat0 = json.loads((ROOT / "output" / f"{p}_seed.json").read_text())["lat"]
            m0, mw = drift_stats(tr0, lat0), drift_stats(trw, lat0)
            stats[p] = {"drift_cs": m0[0], "drift_cs_max": m0[1],
                        "drift_wind": mw[0], "drift_wind_max": mw[1]}
            statf.write_text(json.dumps(stats, indent=2))
            print(f"[{p}] (cached) current+Stokes {m0[0]:.0f} m | +windage {mw[0]:.0f} m", flush=True)
            continue
        ov = OVERRIDES.get(p, {})
        epsg = ov.get("epsg") or json.loads((d / f"{p}_grid.json").read_text())["epsg"]
        trim = d / ov.get("trim", f"trim-{p}.nc")
        wavm = d / ov.get("wavm", f"wavm-{p}.nc")
        wnd = d / ov.get("wnd", f"{p}.wnd")
        args = ["src/cf_export.py", "--flow", trim, "--src-crs", f"EPSG:{epsg}",
                "--lake", p, "--out", forcing]
        if wavm.exists():
            args += ["--wave", wavm]
        if wnd.exists():
            args += ["--wind", wnd]
        print(f"[{p}] export ...", flush=True)
        run(*args)

        # pole-of-inaccessibility seed (same for both demos)
        ds = xr.open_dataset(forcing)
        wet = np.isfinite(ds["u"].isel(time=0, depth=0).values)
        LON, LAT = np.meshgrid(ds.lon.values, ds.lat.values)
        dist = ndimage.distance_transform_edt(wet)
        ji = np.unravel_index(np.argmax(dist), dist.shape)
        lon0, lat0 = float(LON[ji]), float(LAT[ji])
        coslat = np.cos(np.deg2rad(lat0))
        cell_m = abs(float(np.median(np.diff(ds.lon.values)))) * coslat * 111e3
        radius = float(min(300.0, 0.6 * float(dist.max()) * cell_m))
        ds.close()
        (ROOT / "output" / f"{p}_seed.json").write_text(
            json.dumps({"lon": lon0, "lat": lat0, "radius": radius}))

        tr0 = ROOT / "output" / f"{p}_trajectory.nc"          # current + Stokes
        trw = ROOT / "output" / f"{p}_trajectory_wind.nc"     # + 2% windage
        common = ["--forcing", forcing, "--lon", lon0, "--lat", lat0,
                  "--radius", radius, "--hours", 36, "--n", 400]
        run("src/run_opendrift_demo.py", *common, "--wind-drift-factor", 0, "--out", tr0)
        run("src/run_opendrift_demo.py", *common, "--wind-drift-factor", 0.02, "--out", trw)

        m0 = drift_stats(tr0, lat0)
        mw = drift_stats(trw, lat0)
        stats[p] = {"drift_cs": m0[0], "drift_cs_max": m0[1],
                    "drift_wind": mw[0], "drift_wind_max": mw[1]}
        statf.write_text(json.dumps(stats, indent=2))
        print(f"[{p}] current+Stokes {m0[0]:.0f} m | +windage {mw[0]:.0f} m", flush=True)

    print("wrote output/wind_drift_stats.json")


if __name__ == "__main__":
    main()
