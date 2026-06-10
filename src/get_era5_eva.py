"""
get_era5_eva.py -- build a Delft3D-FLOW evaporation/precipitation (.eva) file
from ERA5, closing the surface water + heat balance for the lake.

Delft3D .eva format (FLOW User Manual B.6), 4 free-format columns:
    time [min after ref date]   precipitation [mm/h]   evaporation [mm/h]   rain_temp [C]

Wire into the .mdf (Additional parameters):
    Fileva = #<lake>.eva#
    Evaint = #Y#          (linear interpolation)
    Maseva = #Y#          (add evap/precip to the continuity/MASS balance)

ERA5 source vars (reanalysis-era5-single-levels, hourly accumulations in m):
    total_precipitation   [m/hour]  -> *1000 = mm/h
    evaporation           [m/hour, negative=upward] -> *-1000 = mm/h (loss +)
    2m_temperature        [K] -> -273.15 = rain temp [C]

Usage:
  conda run --no-capture-output -n plastic python src/get_era5_eva.py \
    --lon 21.95 --lat 40.20 --start 2022-07-01 --days 7 --tzone 2 \
    --itdate 2022-07-01 --out models/polyfytos/polifitos.eva
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]
ALL_TIMES = [f"{h:02d}:00" for h in range(24)]


def download(lon, lat, start, end, out_nc):
    import cdsapi
    lo, hi = start - timedelta(days=1), end + timedelta(days=1)
    months = sorted({(d.year, d.month) for d in
                     [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]})
    years = sorted({y for y, _ in months})
    if len(years) != 1:
        raise SystemExit("window spans multiple years; split the request")
    half = 0.13
    req = {
        "product_type": "reanalysis",
        "variable": ["total_precipitation", "evaporation", "2m_temperature"],
        "year": str(years[0]), "month": [f"{m:02d}" for _, m in months],
        "day": ALL_DAYS, "time": ALL_TIMES,
        "area": [lat + half, lon - half, lat - half, lon + half],
        "data_format": "netcdf", "download_format": "unarchived",
    }
    print(f"requesting ERA5 precip/evap/t2m {years[0]} @ ({lon},{lat})")
    cdsapi.Client().retrieve("reanalysis-era5-single-levels", req, str(out_nc))


def _open_era5(path):
    """New CDS returns a ZIP of two .nc (instant + accum) when step types mix."""
    import xarray as xr, zipfile
    if not zipfile.is_zipfile(path):
        return xr.open_dataset(path)
    dss, tmps = [], []
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.endswith(".nc"):
                tmp = Path(path).parent / ("_era5tmp_" + Path(n).name)
                tmp.write_bytes(z.read(n)); tmps.append(tmp)
                dss.append(xr.open_dataset(tmp))
    ds = xr.merge(dss, compat="override", join="outer")
    for t in tmps:
        try: t.unlink()
        except OSError: pass
    return ds


def to_eva(nc, lon, lat, start, end, itdate, tzone, out_eva):
    import xarray as xr
    ds = _open_era5(nc)
    tp = ds["tp"] if "tp" in ds else ds["total_precipitation"]
    ev = ds["e"] if "e" in ds else ds["evaporation"]
    t2 = ds["t2m"] if "t2m" in ds else ds["2m_temperature"]
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    tname = "valid_time" if "valid_time" in ds.coords else "time"
    sel = {latn: lat, lonn: lon}
    tp = tp.sel(sel, method="nearest"); ev = ev.sel(sel, method="nearest")
    t2 = t2.sel(sel, method="nearest")

    t = ds[tname].values.astype("datetime64[s]").astype("O")
    precip = np.asarray(tp.values, float) * 1000.0          # m/h -> mm/h
    evap = -np.asarray(ev.values, float) * 1000.0           # m/h(neg) -> mm/h loss+
    evap = np.clip(evap, 0, None)                            # keep evaporation >= 0
    raintemp = np.asarray(t2.values, float) - 273.15        # K -> C

    lo, hi = start - timedelta(days=1), end + timedelta(days=1)
    m = np.array([(lo <= ti <= hi) for ti in t])
    t = np.array(t)[m]; precip, evap, raintemp = precip[m], evap[m], raintemp[m]
    it0 = datetime.strptime(itdate, "%Y-%m-%d")
    tmin = np.array([((ti + timedelta(hours=tzone)) - it0).total_seconds() / 60.0
                     for ti in t])
    order = np.argsort(tmin)
    tmin, precip, evap, raintemp = tmin[order], precip[order], evap[order], raintemp[order]
    # Delft3D time-dependent data must start at t>=0 (Tstart). Drop the pre-start
    # buffer but keep a record at/just below 0 so t=0 is covered.
    keep = tmin >= 0
    if keep.any() and tmin[keep][0] > 0 and (~keep).any():
        keep[np.where(~keep)[0][-1]] = True   # retain last record just before 0
    tmin, precip, evap, raintemp = tmin[keep], precip[keep], evap[keep], raintemp[keep]

    Path(out_eva).parent.mkdir(parents=True, exist_ok=True)
    with open(out_eva, "w") as fh:
        for tm, pr, ev_, rt in zip(tmin, precip, evap, raintemp):
            fh.write(f" {tm:14.7e}  {pr:12.6e}  {ev_:12.6e}  {rt:10.4f}\n")
    print(f"wrote {out_eva}  ({len(tmin)} records, "
          f"precip {precip.min():.3f}-{precip.max():.3f} mm/h, "
          f"evap {evap.min():.3f}-{evap.max():.3f} mm/h, "
          f"t {raintemp.min():.1f}-{raintemp.max():.1f} C)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--itdate", default=None)
    ap.add_argument("--tzone", type=float, default=0.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-nc", action="store_true")
    args = ap.parse_args()
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = start + timedelta(days=args.days)
    itdate = args.itdate or args.start
    nc = Path(args.out).with_suffix(".eva.nc")
    nc.parent.mkdir(parents=True, exist_ok=True)
    if not nc.exists():
        download(args.lon, args.lat, start, end, nc)
    to_eva(nc, args.lon, args.lat, start, end, itdate, args.tzone, args.out)
    if not args.keep_nc:
        nc.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
