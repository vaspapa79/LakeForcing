"""
get_era5_tem.py -- build a Delft3D-FLOW heat-model (.tem) file from ERA5 for the
Ocean heat flux model (Ktemp=5, Solrad=#Y#).

.tem columns (matches the validated Polyfytos heat file), free-format:
    time[min]   rel_humidity[%]   air_temp[C]   cloud_cover[%]   net_solar[W/m2]

ERA5 source (reanalysis-era5-single-levels, hourly):
    2m_temperature              [K]   -> air temp [C]
    2m_dewpoint_temperature     [K]   -> RH via Magnus(Td,T)
    total_cloud_cover           [0-1] -> *100 = %
    surface_solar_radiation_downwards [J/m2 accum/hour] -> /3600 = W/m2

Usage:
  conda run --no-capture-output -n plastic python src/get_era5_tem.py \
    --lon 18.57 --lat 59.85 --start 2022-07-01 --days 7 --tzone 2 \
    --itdate 2022-07-01 --out models/erken_sweden/erken.tem
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
    if len({y for y, _ in months}) != 1:
        raise SystemExit("window spans multiple years; split the request")
    half = 0.13
    req = {
        "product_type": "reanalysis",
        "variable": ["2m_temperature", "2m_dewpoint_temperature",
                     "total_cloud_cover", "surface_solar_radiation_downwards"],
        "year": str(months[0][0]), "month": [f"{m:02d}" for _, m in months],
        "day": ALL_DAYS, "time": ALL_TIMES,
        "area": [lat + half, lon - half, lat - half, lon + half],
        "data_format": "netcdf", "download_format": "unarchived",
    }
    print(f"requesting ERA5 t2m/d2m/tcc/ssrd @ ({lon},{lat})")
    cdsapi.Client().retrieve("reanalysis-era5-single-levels", req, str(out_nc))


def _open_era5(path):
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


def magnus_rh(t_c, td_c):
    a, b = 17.625, 243.04
    es = np.exp(a * t_c / (b + t_c))
    e = np.exp(a * td_c / (b + td_c))
    return np.clip(100.0 * e / es, 0.0, 100.0)


def to_tem(nc, lon, lat, start, end, itdate, tzone, out_tem):
    ds = _open_era5(nc)
    g = lambda *n: next(ds[k] for k in n if k in ds.variables)
    t2 = g("t2m", "2m_temperature"); d2 = g("d2m", "2m_dewpoint_temperature")
    tcc = g("tcc", "total_cloud_cover"); ssrd = g("ssrd", "surface_solar_radiation_downwards")
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    tname = "valid_time" if "valid_time" in ds.coords else "time"
    sel = {latn: lat, lonn: lon}
    t2 = t2.sel(sel, method="nearest"); d2 = d2.sel(sel, method="nearest")
    tcc = tcc.sel(sel, method="nearest"); ssrd = ssrd.sel(sel, method="nearest")

    tair = np.asarray(t2.values, float) - 273.15
    tdew = np.asarray(d2.values, float) - 273.15
    rh = magnus_rh(tair, tdew)
    cloud = np.clip(np.asarray(tcc.values, float) * 100.0, 0, 100)
    solar = np.clip(np.asarray(ssrd.values, float) / 3600.0, 0, None)  # J/m2/h -> W/m2

    t = ds[tname].values.astype("datetime64[s]").astype("O")
    lo, hi = start - timedelta(days=1), end + timedelta(days=1)
    m = np.array([(lo <= ti <= hi) for ti in t])
    t = np.array(t)[m]; rh, tair, cloud, solar = rh[m], tair[m], cloud[m], solar[m]
    it0 = datetime.strptime(itdate, "%Y-%m-%d")
    tmin = np.array([((ti + timedelta(hours=tzone)) - it0).total_seconds() / 60.0 for ti in t])
    order = np.argsort(tmin)
    tmin, rh, tair, cloud, solar = (a[order] for a in (tmin, rh, tair, cloud, solar))
    keep = tmin >= 0
    if keep.any() and tmin[keep][0] > 0 and (~keep).any():
        keep[np.where(~keep)[0][-1]] = True
    tmin, rh, tair, cloud, solar = (a[keep] for a in (tmin, rh, tair, cloud, solar))

    Path(out_tem).parent.mkdir(parents=True, exist_ok=True)
    with open(out_tem, "w") as fh:
        for tm, r, ta, c, s in zip(tmin, rh, tair, cloud, solar):
            fh.write(f" {tm:13.6e} {r:8.2f} {ta:8.2f} {c:8.2f} {s:10.2f}\n")
    print(f"wrote {out_tem}  ({len(tmin)} rec, RH {rh.min():.0f}-{rh.max():.0f}%, "
          f"Tair {tair.min():.1f}-{tair.max():.1f}C, cloud {cloud.min():.0f}-{cloud.max():.0f}%, "
          f"solar {solar.min():.0f}-{solar.max():.0f} W/m2)")


def main():
    ap = argparse.ArgumentParser()
    for a in ["--lon", "--lat"]:
        ap.add_argument(a, type=float, required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--itdate", default=None)
    ap.add_argument("--tzone", type=float, default=0.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-nc", action="store_true")
    args = ap.parse_args()
    start = datetime.strptime(args.start, "%Y-%m-%d"); end = start + timedelta(days=args.days)
    itdate = args.itdate or args.start
    nc = Path(args.out).with_suffix(".tem.nc"); nc.parent.mkdir(parents=True, exist_ok=True)
    if not nc.exists():
        download(args.lon, args.lat, start, end, nc)
    to_tem(nc, args.lon, args.lat, start, end, itdate, args.tzone, args.out)
    if not args.keep_nc:
        nc.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
