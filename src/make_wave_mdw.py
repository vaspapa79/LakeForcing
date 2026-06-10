"""
make_wave_mdw.py -- generate a Delft3D-WAVE (.mdw) input for a lake, reusing the
existing FLOW curvilinear grid. Stationary, wind-forced SWAN -> fetch-limited
wind waves (Hs, Tp, direction). One-way: no FLOW feedback needed for a forcing
product.

For Polyfytos this reuses polifitos.grd directly. Wind is taken as a single
space-uniform vector per WAVE timepoint (matches the FLOW .wnd forcing); SWAN
grows the wave field over the lake fetch from that wind.

Usage:
    python src/make_wave_mdw.py --grid "C:/.../polifitos.grd" \
        --out "C:/.../Lake Polyfytos/polifitos.mdw" \
        --wind-speed 7.0 --wind-dir 320

This writes inputs ONLY. It does not run anything. Launch when you're ready with:
    "C:/Program Files/Deltares/Delft3D 4.07.01/kernels/x64/bin/run_dwaves.bat" polifitos.mdw
"""
import argparse
from pathlib import Path

MDW = """[WaveFileInformation]
   FileVersion          = 02.00
[General]
   ProjectName          = {name}
   ProjectNr            = 0001
   Description          = Wind-wave forcing for OpenDrift lake dataset
   OnlyInputVerify      = false
   SimMode              = stationary
   DirConvention        = nautical
   ReferenceDate        = {refdate}
[TimePoint]
   Time                 = 0.0
   WaterLevel           = 0.0
   XVeloc               = 0.0
   YVeloc               = 0.0
   WindSpeed            = {wspeed}
   WindDir              = {wdir}
[Constants]
   Gravity              = 9.81
   WaterDensity         = 1000.0
   NorthDir             = 90.0
   MinimumDepth         = 0.05
[Processes]
   GenModePhys          = 3
   WaveSetup            = false
   Breaking             = true
   BreakAlpha           = 1.0
   BreakGamma           = 0.73
   Triads               = false
   BedFriction          = jonswap
   BedFricCoef          = 0.067
   Diffraction          = false
   WindGrowth           = true
   WhiteCapping         = Komen
   Quadruplets          = true
   Refraction           = true
   FreqShift            = true
   WaveForces           = dissipation 3d
[Numerics]
   DirSpaceCDD          = 0.5
   FreqSpaceCSS         = 0.5
   RChHsTm01            = 0.02
   RChMeanHs            = 0.02
   RChMeanTm01          = 0.02
   PercWet              = 98.0
   MaxIter              = 25
[Output]
   TestOutputLevel      = 0
   TraceCalls           = false
   UseHotFile           = false
   MapWriteInterval     = 60.0
   WriteCOM             = false
   COMWriteInterval     = 60.0
[Domain]
   Grid                 = {grid}
   BedLevel             = {dep}
   DirSpace             = circle
   NDir                 = 36
   StartDir             = 0.0
   EndDir               = 360.0
   FreqMin              = 0.05
   FreqMax              = 1.0
   NFreq                = 24
   Output               = true
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True, help="Delft3D .grd")
    ap.add_argument("--dep", help="Delft3D .dep (defaults to grid stem + .dep)")
    ap.add_argument("--out", required=True, help="output .mdw path")
    ap.add_argument("--name", default="lake")
    ap.add_argument("--refdate", default="2022-07-01")
    ap.add_argument("--wind-speed", type=float, default=7.0)
    ap.add_argument("--wind-dir", type=float, default=320.0)
    args = ap.parse_args()

    grid = Path(args.grid)
    dep = args.dep or str(grid.with_suffix(".dep"))
    text = MDW.format(name=args.name, refdate=args.refdate,
                      wspeed=args.wind_speed, wdir=args.wind_dir,
                      grid=grid.name, dep=Path(dep).name)
    Path(args.out).write_text(text)
    print(f"wrote {args.out}")
    print("NOTE: place it beside the .grd/.dep, then (when ready) run:")
    print('  run_dwaves.bat ' + Path(args.out).name)


if __name__ == "__main__":
    main()
