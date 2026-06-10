"""
setup_lake.py -- stage a complete, ready-to-run Delft3D-FLOW+WAVE folder for one
lake from open data: copies the build_grid grid, downloads ERA5 .wnd/.tem/.eva,
generates the .mdf + config_d_hydro.xml + .mdw, and writes run_flow_wave.bat.

After this, the USER only runs FLOW+WAVE (run_flow_wave.bat); then cf_export +
OpenDrift (no Delft3D).

Usage:
  python src/setup_lake.py --prefix balaton --srckey balaton_hungray1 \
     --lon 17.765 --lat 46.866 --tzone 2 --t0 22 \
     [--start 2022-07-01 --days 2 --itdate 2022-07-01 --secchi 5 --wind-speed 6 --wind-dir 270]
"""
import argparse, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
PY = sys.executable
BIN = r"C:\Program Files\Deltares\Delft3D 4.07.01\kernels\x64\bin"

RUN_BAT = """@echo off
REM {prefix}: FLOW then WAVE. You launch this.
setlocal
set "BIN={bin}"
cd /d "%~dp0"
echo === FLOW {prefix} ===
call "%BIN%\\run_dflow2d3d.bat"
if errorlevel 1 ( echo FLOW failed & pause & exit /b 1 )
echo === WAVE {prefix} ===
call "%BIN%\\run_dwaves.bat" {prefix}.mdw
echo === DONE: trim-{prefix}.nc + wavm-{prefix}.nc ===
pause
"""


def run(*cmd):
    cmd = [str(c) for c in cmd]            # subprocess needs str args (not floats)
    print("  $", " ".join(cmd[1:3]), "...")
    r = subprocess.run([PY, *cmd], cwd=ROOT, capture_output=True, text=True)
    tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
    print("   ->", tail[0][:100])
    if r.returncode != 0:
        print("   STDERR:", (r.stderr or "")[-300:])
        raise SystemExit(f"step failed: {cmd[1]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--srckey", required=True, help="models/<srckey> dir with the grid")
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--tzone", type=float, default=0)
    ap.add_argument("--t0", type=float, default=15)
    ap.add_argument("--secchi", type=float, default=5)
    ap.add_argument("--start", default="2022-07-01")
    ap.add_argument("--days", type=int, default=2)
    ap.add_argument("--itdate", default="2022-07-01")
    ap.add_argument("--wind-speed", type=float, default=6)
    ap.add_argument("--wind-dir", type=float, default=270)
    a = ap.parse_args()

    src = ROOT / "models" / a.srckey
    dst = ROOT / "models" / a.prefix
    dst.mkdir(parents=True, exist_ok=True)
    print(f"[{a.prefix}] staging from {a.srckey}")
    for s, d in [(src / f"{a.srckey}{e}", dst / f"{a.prefix}{e}")
                 for e in (".grd", ".dep", ".enc")] + \
                [(src / f"{a.srckey}_grid.json", dst / f"{a.prefix}_grid.json")]:
        if s.resolve() != d.resolve():        # DAHITI lakes: srckey==prefix -> already in place
            shutil.copy(s, d)

    common = ["--lon", a.lon, "--lat", a.lat, "--start", a.start, "--days", a.days,
              "--tzone", a.tzone, "--itdate", a.itdate]
    base = f"models/{a.prefix}/{a.prefix}"
    print(f"[{a.prefix}] ERA5 forcing")
    run("src/get_era5.py", *common, "--out", f"{base}.wnd")
    run("src/get_era5_tem.py", *common, "--out", f"{base}.tem")
    run("src/get_era5_eva.py", *common, "--out", f"{base}.eva")

    print(f"[{a.prefix}] mdf + mdw")
    run("src/make_flow_mdf.py", "--dir", f"models/{a.prefix}", "--prefix", a.prefix,
        "--lat", a.lat, "--itdate", a.itdate, "--tstop", a.days * 1440,
        "--dt", 1, "--tzone", a.tzone, "--t0", a.t0, "--secchi", a.secchi)
    run("src/make_wave_mdw.py", "--grid", f"{base}.grd", "--out", f"{base}.mdw",
        "--name", a.prefix, "--refdate", a.itdate,
        "--wind-speed", a.wind_speed, "--wind-dir", a.wind_dir)

    (dst / "run_flow_wave.bat").write_text(RUN_BAT.format(prefix=a.prefix, bin=BIN))
    print(f"[{a.prefix}] READY -> models/{a.prefix}/ (run_flow_wave.bat)")


if __name__ == "__main__":
    main()
