"""
test_cf_export.py -- exercise the headline sigma-to-z exporter end-to-end on a
small bundled Delft3D fixture, with NO Delft3D installation required. This makes
the most reusable component of the pipeline independently reproducible and
testable: a reviewer (or CI) can run it from a clean checkout.

  pytest tests/test_cf_export.py -q
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
TRIM = FIX / "trim-erken_mini.nc"
WAVM = FIX / "wavm-erken_mini.nc"


def test_cf_export_runs_and_is_cf_compliant(tmp_path):
    assert TRIM.exists() and WAVM.exists(), (
        "fixtures missing -- run `python tests/build_fixture.py` first")
    out = tmp_path / "erken_fixture_forcing.nc"
    cmd = [sys.executable, str(ROOT / "src" / "cf_export.py"),
           "--flow", str(TRIM), "--wave", str(WAVM),
           "--src-crs", "EPSG:32634", "--lake", "erken_fixture",
           "--out", str(out)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"cf_export failed:\n{r.stderr[-2000:]}"
    assert out.exists(), "no output NetCDF written"

    ds = xr.open_dataset(out)
    # CF conventions tag
    assert str(ds.attrs.get("Conventions", "")).startswith("CF"), "missing CF Conventions"
    # the headline 3-D + surface fields are present
    for v in ("u", "v", "temp", "zeta", "Hs"):
        assert v in ds.variables, f"missing exported variable {v}"
    # CF standard_names that OpenDrift's generic reader keys on (x/y == east/north
    # here, since the fields were rotated to geographic axes in the export)
    assert ds["u"].attrs.get("standard_name") == "x_sea_water_velocity"
    assert ds["v"].attrs.get("standard_name") == "y_sea_water_velocity"
    # fixed z-levels in metres, surface at 0, deepening downward, masked below bed
    z = ds["depth"].values
    assert z[0] == 0 and z.min() <= -30, f"unexpected z-levels {z}"
    assert np.all(np.diff(z) < 0), "z-levels must be monotonically downward"
    # regular lon/lat raster, monotonic increasing
    assert np.all(np.diff(ds["lon"].values) > 0)
    assert np.all(np.diff(ds["lat"].values) > 0)
    # surface currents contain real (finite) water cells
    usurf = ds["u"].isel(time=0, depth=0).values
    assert np.isfinite(usurf).sum() > 0, "no wet surface current cells"
    ds.close()
