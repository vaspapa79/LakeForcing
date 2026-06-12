"""
build_fixture.py -- create a small, self-contained Delft3D test fixture so the
sigma-to-z exporter (cf_export.py) can be run and tested WITHOUT installing
Delft3D. Subsets the smallest demonstration lake's trim-*.nc to two time steps
and the variables the exporter reads, and copies the (already tiny) wavm-*.nc.

  python tests/build_fixture.py
"""
import shutil
from pathlib import Path
import xarray as xr

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
SRC = ROOT / "models" / "erken"
DST = ROOT / "tests" / "fixtures"
DST.mkdir(parents=True, exist_ok=True)

# variables read by cf_export.read_trim (+ what they depend on)
KEEP = ["XZ", "YZ", "ALFAS", "S1", "U1", "V1", "SIG_LYR", "DPS", "DP0",
        "KCS", "R1", "NAMCON"]


def main():
    ds = xr.open_dataset(SRC / "trim-erken.nc")
    keep = [v for v in KEEP if v in ds.variables]
    sub = ds[keep]
    if "time" in sub.dims:
        sub = sub.isel(time=slice(0, 2))     # two steps is enough to exercise σ->z
    out = DST / "trim-erken_mini.nc"
    enc = {v: {"zlib": True, "complevel": 4} for v in sub.data_vars}
    sub.to_netcdf(out, encoding=enc)
    ds.close()
    shutil.copy(SRC / "wavm-erken.nc", DST / "wavm-erken_mini.nc")
    tmb = out.stat().st_size / 1048576
    wmb = (DST / "wavm-erken_mini.nc").stat().st_size / 1048576
    print(f"wrote {out.name} ({tmb:.1f} MB), wavm-erken_mini.nc ({wmb:.1f} MB)")
    print("kept vars:", keep)


if __name__ == "__main__":
    main()
