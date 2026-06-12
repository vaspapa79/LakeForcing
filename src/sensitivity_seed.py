"""
sensitivity_seed.py -- robustness of the drift ranking to the release point
(review comment on single-release sensitivity). For each lake we re-run the
current+Stokes demo from an ENSEMBLE of independent interior release points
(not a single alternative, which in a small sheltered basin can land in a
near-stagnant corner and give a misleadingly degenerate value), and compare the
cross-lake ranking of the primary seeding to that of the ensemble median, plus
the within-lake spread.

  conda run -n plastic python src/sensitivity_seed.py
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
import xarray as xr
from scipy import ndimage
from scipy.stats import spearmanr

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
PY = sys.executable
ORDER = ["lagdo", "bornos", "mead", "polyfytos", "trasimeno", "balaton",
         "rotsee", "erken", "poyang", "sea_of_galilee", "eucumbene", "nova_ponte"]
K = 5   # interior seeds per lake


def run(*cmd):
    r = subprocess.run([PY, *map(str, cmd)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stderr or "")[-500:]); raise SystemExit(f"failed {cmd[1]}")


def drift_mean(traj, lat0):
    t = xr.open_dataset(traj); lon, lat = t["lon"].values, t["lat"].values
    dd = np.sqrt(((lon[:, -1] - lon[:, 0]) * np.cos(np.deg2rad(lat0)) * 111e3) ** 2
                 + ((lat[:, -1] - lat[:, 0]) * 111e3) ** 2)
    t.close(); dd = dd[np.isfinite(dd)]
    return float(dd.mean()) if dd.size else 0.0


prim = json.loads((ROOT / "output" / "wind_drift_stats.json").read_text())
ens = {}
for li, p in enumerate(ORDER):
    f = ROOT / "output" / f"{p}_forcing.nc"
    ds = xr.open_dataset(f)
    wet = np.isfinite(ds["u"].isel(time=0, depth=0).values)
    LON, LAT = np.meshgrid(ds.lon.values, ds.lat.values)
    dist = ndimage.distance_transform_edt(wet)
    dmax = float(dist.max())
    coslat0 = np.cos(np.deg2rad(float(LAT[np.unravel_index(np.argmax(dist), dist.shape)])))
    cell_m = abs(float(np.median(np.diff(ds.lon.values)))) * coslat0 * 111e3
    # candidate interior cells: at least half the maximum clearance from shore
    cand = np.argwhere(dist >= 0.5 * dmax)
    rng = np.random.RandomState(100 + li)            # reproducible per lake
    pick = cand[rng.choice(len(cand), size=min(K, len(cand)), replace=False)]
    ds.close()
    drifts = []
    for si, (jy, jx) in enumerate(pick):
        lon0, lat0 = float(LON[jy, jx]), float(LAT[jy, jx])
        radius = float(min(300.0, max(60.0, 0.6 * float(dist[jy, jx]) * cell_m)))
        traj = ROOT / "output" / f"{p}_ens{si}.nc"
        run("src/run_opendrift_demo.py", "--forcing", f, "--lon", lon0, "--lat", lat0,
            "--radius", radius, "--hours", 36, "--n", 300,
            "--wind-drift-factor", 0, "--out", traj)
        drifts.append(drift_mean(traj, lat0))
    ens[p] = drifts
    md = float(np.median(drifts))
    print(f"[{p:15s}] primary {prim[p]['drift_cs']:5.0f} | ensemble median {md:5.0f} "
          f"(min {min(drifts):.0f}, max {max(drifts):.0f})", flush=True)

x = [prim[p]["drift_cs"] for p in ORDER]
ymed = [float(np.median(ens[p])) for p in ORDER]
rho, pval = spearmanr(x, ymed)
# within-lake spread: median across lakes of (IQR / median) for non-degenerate lakes
cvs = []
for p in ORDER:
    a = np.array(ens[p]); m = np.median(a)
    if m > 50:
        cvs.append(float((np.percentile(a, 75) - np.percentile(a, 25)) / m))
out = {"ensemble_drift": ens, "ensemble_median": {p: float(np.median(ens[p])) for p in ORDER},
       "spearman_primary_vs_ensemble_median": float(rho), "p": float(pval),
       "median_within_lake_relative_IQR": float(np.median(cvs)), "K": K}
(ROOT / "output" / "sensitivity_seed.json").write_text(json.dumps(out, indent=2))
print(f"\nCross-lake ranking Spearman (primary vs {K}-seed ensemble median): "
      f"rho = {rho:.3f} (p = {pval:.4f})")
print(f"Median within-lake relative IQR: {np.median(cvs):.2f}")
