"""
cf_export.py  --  Delft3D (sigma) -> OpenDrift (z-level) CF-NetCDF exporter.

This is the heart of the pipeline: it resolves the vertical-coordinate mismatch
between Delft3D-FLOW (terrain-following sigma layers) and OpenDrift (fixed depth
levels in metres), and packages currents + temperature + waves + wind into one
CF-compliant NetCDF that `reader_netCDF_CF_generic` reads directly.

Three regrids happen here:
  (1) VERTICAL   sigma -> fixed z-levels   (the issue you flagged)
  (2) HORIZONTAL Delft3D curvilinear grid -> regular lon/lat raster
  (3) ROTATION   grid-oriented (xi,eta) velocities -> east/north
                 (OpenDrift's x_sea_water_velocity == eastward)

Input : a Delft3D-FLOW NetCDF map file (trim-<run>.nc).
        To get one, add this line to the .mdf and re-run FLOW:
            FlNcdf = #map his#
        (otherwise FLOW writes NEFIS trim-<run>.dat/.def, which must be
         converted first; see SETUP_NOTES.md).
Output: <lake>_forcing.nc  (CF, OpenDrift-ready, z negative-down).

NOTE ON VARIABLE NAMES: Delft3D trim-NetCDF variable names are stable across
4.0x but the exact sigma sign convention and U/V staggering are worth a 10-second
check against the first real trim file (see `_VERIFY` markers). The transform
maths below are the reusable, correct core; the I/O mapping is a one-line fix if
a name differs in your build.
"""

from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import xarray as xr
from scipy.interpolate import griddata
from pyproj import Transformer

# ---- target vertical grid (metres, negative down). z=0 == surface (floating) ----
Z_LEVELS = np.array([0.0, -1.0, -2.0, -3.0, -5.0, -7.5, -10.0,
                     -15.0, -20.0, -30.0, -50.0], dtype="f4")

G = 9.81  # gravity


# --------------------------------------------------------------------------- #
#  1. read Delft3D-FLOW trim NetCDF
# --------------------------------------------------------------------------- #
def read_trim(path: Path, src_crs: str):
    """Pull the fields we need out of a Delft3D trim-*.nc map file."""
    ds = xr.open_dataset(path)

    # cell-centre horizontal coords (projected, model CRS), shape (N, M)
    xz = ds["XZ"].values            # easting  (m)
    yz = ds["YZ"].values            # northing (m)
    alfas = np.deg2rad(ds["ALFAS"].values)   # grid orientation per cell (deg->rad)

    s1 = ds["S1"].values            # water level (time, N, M)
    u1 = ds["U1"].values            # xi-velocity at U-points  (time, K, N, M)  _VERIFY
    v1 = ds["V1"].values            # eta-velocity at V-points (time, K, N, M)  _VERIFY

    # sigma layer centres (fraction). Delft3D: 0 at surface -> -1 at bed.  _VERIFY sign
    sig = ds["SIG_LYR"].values      # (K,)
    if sig.max() > 0:               # some builds store 0..1 positive-down
        sig = -sig

    # still-water bed depth below datum, positive down, at cell centre
    dps = ds["DPS"].values if "DPS" in ds else ds["DP0"].values   # (N, M)

    # active-cell mask (KCS==1). Inactive/dummy cells have XZ=YZ=0 and would
    # pollute the lon/lat extent (spurious points near the equator/zone meridian).
    kcs = ds["KCS"].values if "KCS" in ds else None

    # temperature constituent out of R1 (time, LSTSCI, K, N, M); find by name
    temp = None
    if "R1" in ds:
        names = [str(n) for n in ds.get("NAMCON", xr.DataArray([])).values]
        for i, nm in enumerate(names):
            if "temp" in nm.lower():
                temp = ds["R1"].values[:, i]      # (time, K, N, M)
                break

    time = ds["time"].values
    ds.close()

    # destagger velocities to cell centres. VERIFIED against real trim:
    #   U1 dims (time,K,MC,N) -> U staggered on M axis (-2)
    #   V1 dims (time,K,M,NC) -> V staggered on N axis (-1)
    u_c = _destagger(u1, axis_m=-2)   # average along M (xi) direction
    v_c = _destagger(v1, axis_m=-1)   # average along N (eta) direction

    # rotate (xi, eta) -> (east, north) per cell using grid angle ALFAS
    ca, sa = np.cos(alfas), np.sin(alfas)
    u_east = u_c * ca - v_c * sa
    v_north = u_c * sa + v_c * ca

    # reproject cell centres -> lon/lat, masking inactive/dummy cells to NaN
    tr = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)
    lon, lat = tr.transform(xz, yz)
    bad = (xz == 0) & (yz == 0)
    if kcs is not None:
        bad = bad | (kcs != 1)
    lon = np.where(bad, np.nan, lon)
    lat = np.where(bad, np.nan, lat)

    return dict(time=time, lon=lon, lat=lat, sig=sig, s1=s1, dps=dps,
                u=u_east, v=v_north, temp=temp)


def _destagger(a, axis_m):
    """2-point centred average to move a velocity from its face to cell centre."""
    a = np.asarray(a, dtype="f4")
    sl_lo = [slice(None)] * a.ndim
    sl_hi = [slice(None)] * a.ndim
    sl_lo[axis_m] = slice(0, -1)
    sl_hi[axis_m] = slice(1, None)
    out = np.full_like(a, np.nan)
    avg = 0.5 * (a[tuple(sl_lo)] + a[tuple(sl_hi)])
    sl_put = [slice(None)] * a.ndim
    sl_put[axis_m] = slice(1, None)
    out[tuple(sl_put)] = avg
    return out


# --------------------------------------------------------------------------- #
#  2. VERTICAL: sigma -> fixed z-levels   (the core fix)
# --------------------------------------------------------------------------- #
def sigma_to_z(field, s1, dps, sig, z_levels=Z_LEVELS):
    """
    Interpolate a sigma-layer field (time, K, N, M) onto fixed z-levels.

    Physical depth of sigma centre k at cell (n,m), time t:
        H   = s1 + dps                       # total water-column thickness
        z_k = s1 + sig_k * H                 # geoid-referenced, up-positive
              (sig_k in [0,-1]; surface->s1, bed-> s1 - H == -dps)
    Levels below the local bed are masked (NaN).
    """
    nt, nk, nn, nm = field.shape
    nz = len(z_levels)
    out = np.full((nt, nz, nn, nm), np.nan, dtype="f4")

    for t in range(nt):
        H = s1[t] + dps                       # (N, M)
        for n in range(nn):
            for m in range(nm):
                h = H[n, m]
                if not np.isfinite(h) or h <= 0:
                    continue
                zc = s1[t, n, m] + sig * h     # (K,) layer-centre depths
                col = field[t, :, n, m]        # (K,)
                good = np.isfinite(col)
                if good.sum() < 2:
                    continue
                # np.interp needs ascending x -> sort by depth (bed..surface)
                order = np.argsort(zc[good])
                zk, ck = zc[good][order], col[good][order]
                # clamp to endpoints (the shallowest sigma centre is just BELOW
                # z=0, so plain interp would NaN the surface -> fatal for floating
                # particles). Then mask only truly out-of-water target levels.
                vals = np.interp(z_levels, zk, ck)
                below = z_levels < (s1[t, n, m] - h)       # below the bed
                above = z_levels > (s1[t, n, m] + 0.5)     # clearly above surface
                vals[below | above] = np.nan
                out[t, :, n, m] = vals
    return out


# --------------------------------------------------------------------------- #
#  3. HORIZONTAL: curvilinear -> regular lon/lat raster
# --------------------------------------------------------------------------- #
def make_regular_grid(lon, lat, n_target=200):
    """Regular lon/lat grid spanning the model footprint, ~model resolution."""
    lo0, lo1 = np.nanmin(lon), np.nanmax(lon)
    la0, la1 = np.nanmin(lat), np.nanmax(lat)
    # keep cells roughly square in degrees
    aspect = (lo1 - lo0) / max(la1 - la0, 1e-9)
    nx = int(n_target * np.sqrt(aspect))
    ny = int(n_target / np.sqrt(aspect))
    glon = np.linspace(lo0, lo1, max(nx, 20))
    glat = np.linspace(la0, la1, max(ny, 20))
    return glon, glat


def regrid_h(field, lon, lat, glon, glat):
    """
    Interpolate a (..., N, M) curvilinear field onto regular (glat, glon).
    Leading dims (time, z) are looped; returns (..., len(glat), len(glon)).
    """
    flon, flat = lon.ravel(), lat.ravel()
    cfin = np.isfinite(flon) & np.isfinite(flat)        # drop masked-coord points
    pts = np.column_stack([flon, flat])
    GX, GY = np.meshgrid(glon, glat)
    lead = field.shape[:-2]
    out = np.full(lead + GX.shape, np.nan, dtype="f4")
    for idx in np.ndindex(*lead):
        v = field[idx].ravel()
        good = np.isfinite(v) & cfin
        if good.sum() < 4:
            continue
        out[idx] = griddata(pts[good], v[good], (GX, GY), method="linear")
    return out


# --------------------------------------------------------------------------- #
#  4. waves -> Stokes drift  (surface, deep-water monochromatic estimate)
# --------------------------------------------------------------------------- #
def stokes_surface(hs, tp, wave_to_dir_deg):
    """
    Surface Stokes drift components from Hs, Tp, propagation direction.
        omega = 2*pi/Tp ;  k = omega^2/g ;  a = Hs/(2*sqrt(2))
        |Us|  = omega * k * a^2
    Direction = wave 'to' direction (where waves go). Returns (us_e, us_n).
    """
    # validity: real waves only. Tp->0 at the dry/wet interpolation boundary
    # makes omega,k blow up -> guard with a minimum period and an Hs floor.
    hs = np.where(np.isfinite(hs) & (hs > 0.0), hs, 0.0)
    valid = np.isfinite(tp) & (tp > 0.2)
    tp_s = np.where(valid, tp, np.inf)          # inf -> omega 0 -> mag 0
    with np.errstate(divide="ignore", invalid="ignore"):
        omega = 2 * np.pi / tp_s
        k = omega ** 2 / G
        a = hs / (2 * np.sqrt(2))
        mag = omega * k * a ** 2
    mag = np.nan_to_num(mag, nan=0.0, posinf=0.0)
    mag = np.clip(mag, 0.0, 1.0)                 # physical safety cap (m/s)
    th = np.deg2rad(np.nan_to_num(wave_to_dir_deg, nan=0.0))
    return mag * np.sin(th), mag * np.cos(th)   # east, north


# --------------------------------------------------------------------------- #
#  5. write CF NetCDF
# --------------------------------------------------------------------------- #
def write_cf(out_path, time, glon, glat, z, data2d, data3d, attrs):
    """data3d: dict name->(t,z,y,x); data2d: dict name->(t,y,x). With CF names."""
    coords = dict(
        time=("time", time),
        depth=("depth", z.astype("f4"),
               {"standard_name": "depth", "units": "m", "positive": "down"}),
        lat=("lat", glat.astype("f4"),
             {"standard_name": "latitude", "units": "degrees_north"}),
        lon=("lon", glon.astype("f4"),
             {"standard_name": "longitude", "units": "degrees_east"}),
    )
    cf = {
        "u": "x_sea_water_velocity", "v": "y_sea_water_velocity",
        "temp": "sea_water_temperature",
        "zeta": "sea_surface_height_above_geoid",
        "Hs": "sea_surface_wave_significant_height",
        "Tp": "sea_surface_wave_period_at_variance_spectral_density_maximum",
        "wdir": "sea_surface_wave_to_direction",
        "ust": "sea_surface_wave_stokes_drift_x_velocity",
        "vst": "sea_surface_wave_stokes_drift_y_velocity",
    }
    units = {"u": "m s-1", "v": "m s-1", "temp": "degC", "zeta": "m",
             "Hs": "m", "Tp": "s", "wdir": "degree", "ust": "m s-1", "vst": "m s-1"}

    dvars = {}
    for nm, arr in data3d.items():
        dvars[nm] = (("time", "depth", "lat", "lon"), arr,
                     {"standard_name": cf.get(nm, nm), "units": units.get(nm, "1")})
    for nm, arr in data2d.items():
        dvars[nm] = (("time", "lat", "lon"), arr,
                     {"standard_name": cf.get(nm, nm), "units": units.get(nm, "1")})

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    ds = xr.Dataset(dvars, coords=coords, attrs=attrs)
    ds["time"].attrs["standard_name"] = "time"
    enc = {k: {"zlib": True, "complevel": 4, "_FillValue": np.float32(np.nan)}
           for k in dvars}
    ds.to_netcdf(out_path, encoding=enc)
    print(f"wrote {out_path}")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", required=True, help="Delft3D-FLOW trim-*.nc")
    ap.add_argument("--wave", help="Delft3D-WAVE wavm-*.nc (optional)")
    ap.add_argument("--src-crs", default="EPSG:32634")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lake", default="lake")
    args = ap.parse_args()

    f = read_trim(Path(args.flow), args.src_crs)
    glon, glat = make_regular_grid(f["lon"], f["lat"])

    # vertical sigma->z, then horizontal curvilinear->regular
    print("vertical regrid (sigma -> z) ...")
    uz = sigma_to_z(f["u"], f["s1"], f["dps"], f["sig"])
    vz = sigma_to_z(f["v"], f["s1"], f["dps"], f["sig"])
    tz = sigma_to_z(f["temp"], f["s1"], f["dps"], f["sig"]) if f["temp"] is not None else None

    print("horizontal regrid (curvilinear -> regular) ...")
    data3d = {"u": regrid_h(uz, f["lon"], f["lat"], glon, glat),
              "v": regrid_h(vz, f["lon"], f["lat"], glon, glat)}
    if tz is not None:
        # cap the thin-near-shore-cell solar-heating artefact to a physical range
        data3d["temp"] = np.clip(regrid_h(tz, f["lon"], f["lat"], glon, glat), -2.0, 35.0)

    data2d = {"zeta": regrid_h(f["s1"], f["lon"], f["lat"], glon, glat)}

    # ---- waves (optional) ----
    # Delft3D-WAVE output: vars hsign/rtp/dir on its OWN grid (x,y in src CRS),
    # dims (time,nmax,mmax). Our WAVE grid differs from FLOW's, so read the wave
    # grid's own coords. Stationary run -> 1 time step; broadcast to FLOW times.
    if args.wave:
        w = xr.open_dataset(args.wave)
        def wv(*names):
            for n in names:
                if n in w.variables:
                    return np.asarray(w[n].values, float)
            raise KeyError(names)
        hs, tp, wd = wv("hsign", "HSIGN"), wv("rtp", "RTP", "period"), wv("dir", "DIR")
        wx, wy = w["x"].values, w["y"].values
        trw = Transformer.from_crs(args.src_crs, "EPSG:4326", always_xy=True)
        wlon, wlat = trw.transform(wx, wy)
        nt = len(f["time"])

        def reg_broadcast(a):
            a2 = a[0] if a.ndim == 3 else a              # (nmax,mmax)
            r = regrid_h(a2[None], wlon, wlat, glon, glat)[0]   # (ny,nx)
            return np.broadcast_to(r, (nt,) + r.shape).copy()

        hs_r, tp_r, wd_r = reg_broadcast(hs), reg_broadcast(tp), reg_broadcast(wd)
        hs_r[hs_r <= 0] = np.nan                          # SWAN dry cells = 0
        ust, vst = stokes_surface(hs_r, tp_r, wd_r)
        data2d.update(Hs=hs_r, Tp=tp_r, wdir=wd_r, ust=ust, vst=vst)
        w.close()

    attrs = dict(
        title=f"{args.lake}: hydrodynamic + wave forcing for OpenDrift",
        source="Delft3D-FLOW + Delft3D-WAVE (SWAN); sigma->z regridded",
        Conventions="CF-1.8",
        institution="LakeForcing-OpenDrift dataset",
    )
    write_cf(Path(args.out), f["time"], glon, glat, Z_LEVELS, data2d, data3d, attrs)


if __name__ == "__main__":
    main()
