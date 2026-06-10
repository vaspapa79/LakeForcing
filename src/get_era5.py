"""
get_era5.py -- ERA5 10 m wind -> Delft3D-4 uniform wind file (.wnd).

Downloads ERA5 hourly 10 m u/v at a lake centroid for the model window and writes
the space-uniform .wnd Delft3D-FLOW expects:
    <time_min>  <speed m/s>  <direction deg, nautical FROM>
with time in minutes since Itdate (Tunit=M). A +-1 day buffer is fetched so the
series brackets [Tstart, Tstop]. Uses the existing CDS credentials (~/.cdsapirc).

ERA5 is UTC; pass --tzone to match the model's Tzone (e.g. Polyfytos Tzone=2).

Usage (Polyfytos prototype window):
  conda run --no-capture-output -n plastic python src/get_era5.py \
    --lon 21.95 --lat 40.20 --start 2022-07-01 --days 7 --tzone 2 \
    --itdate 2022-07-01 --out models/_era5/polyfytos.wnd
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

ALL_DAYS = [f"{d:02d}" for d in range(1, 32)]
ALL_TIMES = [f"{h:02d}:00" for h in range(24)]


def download(lon, lat, start, end, out_nc):
    import cdsapi
    # include the +-1 day buffer's months so the series brackets Tstart even when
    # the run starts on a month boundary (e.g. 1 Jul needs 30 Jun -> month 06).
    lo, hi = start - timedelta(days=1), end + timedelta(days=1)
    months = sorted({(d.year, d.month) for d in
                     [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]})
    years = sorted({y for y, _ in months})
    if len(years) != 1:
        raise SystemExit("window spans multiple years; split the request")
    mlist = [f"{m:02d}" for _, m in months]
    half = 0.13                                   # ensure >=1 cell at 0.25 deg
    area = [lat + half, lon - half, lat - half, lon + half]   # N W S E
    req = {
        "product_type": "reanalysis",
        "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
        "year": str(years[0]), "month": mlist, "day": ALL_DAYS, "time": ALL_TIMES,
        "area": area, "data_format": "netcdf", "download_format": "unarchived",
    }
    print(f"requesting ERA5 10 m winds {years[0]} months {mlist} @ ({lon},{lat})")
    cdsapi.Client().retrieve("reanalysis-era5-single-levels", req, str(out_nc))


def to_wnd(nc, lon, lat, start, end, itdate, tzone, out_wnd):
    import xarray as xr
    ds = xr.open_dataset(nc)
    # name harmonization across CDS variants
    u = ds["u10" if "u10" in ds else "10m_u_component_of_wind"]
    v = ds["v10" if "v10" in ds else "10m_v_component_of_wind"]
    tname = "valid_time" if "valid_time" in ds.coords else "time"
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    u = u.sel({latn: lat, lonn: lon}, method="nearest")
    v = v.sel({latn: lat, lonn: lon}, method="nearest")

    t = ds[tname].values.astype("datetime64[s]").astype("O")
    uu, vv = np.asarray(u.values, float), np.asarray(v.values, float)
    lo, hi = start - timedelta(days=1), end + timedelta(days=1)
    m = np.array([(lo <= ti <= hi) for ti in t])
    t, uu, vv = np.array(t)[m], uu[m], vv[m]

    speed = np.hypot(uu, vv)
    direction = (np.degrees(np.arctan2(-uu, -vv))) % 360.0   # nautical FROM
    it0 = datetime.strptime(itdate, "%Y-%m-%d")
    tmin = np.array([((ti + timedelta(hours=tzone)) - it0).total_seconds() / 60.0
                     for ti in t])
    order = np.argsort(tmin)
    tmin, speed, direction = tmin[order], speed[order], direction[order]
    # Delft3D time-dependent data must start at t>=0; drop the pre-start buffer
    # but keep the last record just before 0 so t=0 is covered.
    keep = tmin >= 0
    if keep.any() and tmin[keep][0] > 0 and (~keep).any():
        keep[np.where(~keep)[0][-1]] = True
    tmin, speed, direction = tmin[keep], speed[keep], direction[keep]

    Path(out_wnd).parent.mkdir(parents=True, exist_ok=True)
    with open(out_wnd, "w") as fh:
        for tm, sp, dr in zip(tmin, speed, direction):
            fh.write(f" {tm:14.7e}  {sp:14.7e}  {dr:14.7e}\n")
    print(f"wrote {out_wnd}  ({len(tmin)} records, "
          f"speed {speed.min():.1f}-{speed.max():.1f} m/s, "
          f"t {tmin.min():.0f}..{tmin.max():.0f} min)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--itdate", default=None, help="model Itdate (default=start)")
    ap.add_argument("--tzone", type=float, default=0.0)
    ap.add_argument("--out", required=True, help=".wnd output path")
    ap.add_argument("--keep-nc", action="store_true")
    args = ap.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = start + timedelta(days=args.days)
    itdate = args.itdate or args.start
    nc = Path(args.out).with_suffix(".era5.nc")
    nc.parent.mkdir(parents=True, exist_ok=True)
    if not nc.exists():
        download(args.lon, args.lat, start, end, nc)
    to_wnd(nc, args.lon, args.lat, start, end, itdate, args.tzone, args.out)
    if not args.keep_nc:
        nc.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
