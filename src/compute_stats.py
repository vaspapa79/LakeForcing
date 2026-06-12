"""
compute_stats.py -- per-lake morphometric/forcing predictors + Spearman rank
correlations of 36-h drift against them (review comment #23). Also dumps the
mean-depth / mean-wind values needed for Table 3 and Fig. 7a.
"""
import json
from pathlib import Path
import numpy as np
import xarray as xr
from scipy.stats import spearmanr

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
from make_figures import LAKES  # dmax, dmean per lake

ORDER = ["lagdo", "bornos", "mead", "polyfytos", "trasimeno", "balaton",
         "rotsee", "erken", "poyang", "sea_of_galilee", "eucumbene", "nova_ponte"]
WND = {"polyfytos": "polifitos.wnd"}

drift = json.loads((ROOT / "output" / "wind_drift_stats.json").read_text())

rows = {}
for p in ORDER:
    # mean 10 m wind speed from the uniform .wnd
    wpath = ROOT / "models" / p / WND.get(p, f"{p}.wnd")
    a = np.loadtxt(wpath)
    mean_wind = float(np.mean(a[:, 1]))
    # surface area + max fetch from the forcing wet mask
    ds = xr.open_dataset(ROOT / "output" / f"{p}_forcing.nc")
    wet = np.isfinite(ds["u"].isel(time=0, depth=0).values)
    lat0 = float(np.nanmean(ds.lat.values))
    dx = abs(float(np.median(np.diff(ds.lon.values)))) * np.cos(np.deg2rad(lat0)) * 111.0  # km
    dy = abs(float(np.median(np.diff(ds.lat.values)))) * 111.0
    area = float(wet.sum()) * dx * dy                       # km^2
    rows_idx = np.where(wet.any(axis=1))[0]
    cols_idx = np.where(wet.any(axis=0))[0]
    fetch = max((cols_idx[-1]-cols_idx[0]) * dx, (rows_idx[-1]-rows_idx[0]) * dy)  # km
    ds.close()
    rows[p] = dict(dmean=LAKES[p]["dmean"], dmax=LAKES[p]["dmax"],
                   wind=mean_wind, area=area, fetch=fetch,
                   drift_cs=drift[p]["drift_cs"], drift_wind=drift[p]["drift_wind"])

print(f"{'lake':16} {'dmean':>5} {'dmax':>4} {'wind':>5} {'area_km2':>9} {'fetch_km':>8} {'drift_cs':>8}")
for p in ORDER:
    r = rows[p]
    print(f"{p:16} {r['dmean']:5.1f} {r['dmax']:4.0f} {r['wind']:5.1f} {r['area']:9.1f} "
          f"{r['fetch']:8.1f} {r['drift_cs']:8.0f}")

d_cs = np.array([rows[p]["drift_cs"] for p in ORDER])
print("\nSpearman rho (36-h current+Stokes drift vs predictor):")
for key, lab in [("dmean", "mean depth"), ("dmax", "max depth"),
                 ("area", "surface area"), ("fetch", "max fetch"),
                 ("wind", "mean wind speed")]:
    x = np.array([rows[p][key] for p in ORDER])
    rho, pval = spearmanr(x, d_cs)
    print(f"  {lab:16}: rho = {rho:+.2f}  (p = {pval:.3f})")

(ROOT / "output" / "lake_predictors.json").write_text(json.dumps(rows, indent=2))
print("\nwrote output/lake_predictors.json")
