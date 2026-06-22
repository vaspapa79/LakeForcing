"""
make_flow_mdf.py -- generate a Delft3D-FLOW .mdf + config_d_hydro.xml for a
CLOSED, wind+heat-forced lake, from a build_grid.py grid (.grd/.dep/.enc).

Closed lake = no open boundaries, no discharges (simpler than the Polyfytos river
case). Physics templated from the *validated* Polyfytos model:
  - Ocean heat flux model (Ktemp=5), Dalton=Stanton=0.0013, Secchi=5 m, Solrad=Y
  - k-epsilon turbulence, sigma layers
  - evaporation/precip mass balance via Fileva + Maseva (the .eva fix)
Freshwater: salinity refs set to 0. Coriolis uses the real lake latitude (Anglat).

Inputs expected beside the grid (same prefix): <pre>.grd/.dep/.enc and the ERA5
forcing <pre>.wnd / <pre>.tem / <pre>.eva.

Usage:
  python src/make_flow_mdf.py --dir models/erken_sweden --prefix erken \
     --lat 59.845 --itdate 2022-07-01 --tstop 2880 --dt 1 --tzone 2 --t0 15
"""
import argparse, json
from pathlib import Path

# 14 sigma layers (fraction %), fine at the surface — reused from Polyfytos.
THICK = [0.2, 0.2, 0.2, 0.4, 0.5, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 20.0, 20.0, 20.0]

CONFIG_XML = """<?xml version="1.0" encoding="iso-8859-1"?>
<deltaresHydro xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://schemas.deltares.nl/deltaresHydro.xsd">
   <control>
      <sequence>
         <start>Flow2D3D</start>
      </sequence>
   </control>
   <flow2D3D name="Flow2D3D">
      <library>flow2d3d</library>
      <mdfFile>{prefix}.mdf</mdfFile>
   </flow2D3D>
</deltaresHydro>
"""


def fmt_layers(vals, fmt="  %.7e"):
    return "\n".join((" " * 10 if i else "") + (fmt % v).strip()
                     if i == 0 else " " * 10 + (fmt % v).strip()
                     for i, v in enumerate(vals))


def e3(v):
    """Delft3D-style float: 3-digit exponent (e.g. 5.9845000e+001), as Polyfytos."""
    s = f"{v:.7e}"
    m, e = s.split("e")
    return f"{m}e{e[0]}{int(e[1:]):03d}"


def col(vals):
    out = []
    for i, v in enumerate(vals):
        out.append(("" if i == 0 else "          ") + e3(v))
    return "\n".join(out)


def build_mdf(prefix, M, N, K, lat, itdate, tstop, dt, tzone, t0, secchi):
    thick = THICK if K == len(THICK) else [100.0 / K] * K
    layers = lambda v: col([v] * K)
    txt = f"""Ident  = #Delft3D-FLOW 3.59.01.57433#
Commnt =
Runtxt = #LakeForcing closed-lake scenario#
         #{prefix}#
Filcco = #{prefix}.grd#
Anglat =  {e3(lat)}
Grdang =  0.0000000e+000
Filgrd = #{prefix}.enc#
MNKmax = {M} {N} {K}
Thick  = {col(thick)}
Fildep = #{prefix}.dep#
Commnt =                 no. dry points: 0
Commnt =                 no. thin dams: 0
Itdate = #{itdate}#
Tunit  = #M#
Tstart =  0.0000000e+000
Tstop  =  {e3(tstop)}
Dt     = {dt:g}
Tzone  = {tzone:g}
Sub1   = # T  #
Sub2   = #    #
Wnsvwp = #N#
Filwnd = #{prefix}.wnd#
Wndint = #Y#
Zeta0  =  0.0000000e+000
T0     = {layers(t0)}
Salw   =  0.0000000e+000
Tempw  =  {e3(t0)}
Ag     =  9.8100000e+000
Rhow   =  1.0000000e+003
Rhoa   =  1.2000000e+000
Betac  =  5.0000000e-001
Wstres =  6.3000000e-004  0.0000000e+000  4.2900000e-003  1.0000000e+001  4.9500000e-003  2.0000000e+001
Equili = #N#
Tkemod = #K-epsilon   #
Ktemp  = 5
Fclou  =  0.0000000e+000
Sarea  =  0.0000000e+000
Secchi =  {e3(secchi)}
Stantn =  1.3000000e-003
Dalton =  1.3000000e-003
Filtmp = #{prefix}.tem#
Solrad = #Y#
Temint = #Y#
Fileva = #{prefix}.eva#
Evaint = #Y#
Maseva = #Y#
QEvap  = #computed#
Commnt =                 no. open boundaries: 0
Roumet = #C#
Ccofu  =  6.5000000e+001
Ccofv  =  6.5000000e+001
Xlo    =  0.0000000e+000
Vicouv =  2.0000000e-001
Dicouv =  2.0000000e-002
Htur2d = #N#
Vicoww =  2.0000000e-003
Dicoww =  2.0000000e-004
Irov   = 0
Iter   =      2
Dryflp = #YES#
Dpsopt = #MAX#
Dpuopt = #MEAN#
Dryflc =  1.0000000e-001
Dco    = -9.9900000e+002
Tlfsmo =  6.0000000e+001
ThetQH =  0.0000000e+000
Forfuv = #Y#
Forfww = #Y#
Sigcor = #N#
Trasol = #Cyclic-method#
Momsol = #Cyclic#
Commnt =                 no. discharges: 0
Commnt =                 no. observation points: 0
Commnt =                 no. drogues: 0
Commnt =                 no. cross sections: 0
SMhydr = #YYYYY#
SMderv = #YYYYYY#
SMproc = #YYYYYYYYYY#
PMhydr = #NNNNNN#
PMderv = #NNN#
PMproc = #NNNNNNNNNN#
SHhydr = #YYYY#
SHderv = #YYYYY#
SHproc = #YYYYYYYYYY#
SHflux = #YYYY#
Flmap  =  0.0000000e+000 60  {e3(tstop)}
Flhis  =  0.0000000e+000 1440  {e3(tstop)}
Flpp   =  0.0000000e+000 60  {e3(tstop)}
Flrst  = 1440
FlNcdf = #map his#
Online = #N#
"""
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="model dir (has <prefix>.grd etc.)")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--lat", type=float, required=True, help="lake latitude (Coriolis)")
    ap.add_argument("--itdate", default="2022-07-01")
    ap.add_argument("--tstop", type=float, default=2880.0, help="minutes")
    ap.add_argument("--dt", type=float, default=1.0)
    ap.add_argument("--tzone", type=float, default=0.0)
    ap.add_argument("--t0", type=float, default=15.0, help="initial water temp [C]")
    ap.add_argument("--layers", type=int, default=14)
    ap.add_argument("--secchi", type=float, default=5.0)
    args = ap.parse_args()

    d = Path(args.dir)
    gj = json.loads((d / f"{args.prefix}_grid.json").read_text())
    M, N = gj["mdf_MNKmax"][0], gj["mdf_MNKmax"][1]
    K = args.layers
    txt = build_mdf(args.prefix, M, N, K, args.lat, args.itdate,
                    args.tstop, args.dt, args.tzone, args.t0, args.secchi)
    (d / f"{args.prefix}.mdf").write_text(txt)
    (d / "config_d_hydro.xml").write_text(CONFIG_XML.format(prefix=args.prefix))
    print(f"wrote {d/args.prefix}.mdf  (MNKmax {M} {N} {K}, Itdate {args.itdate}, "
          f"Tstop {args.tstop:.0f} min, Anglat {args.lat})")
    print(f"wrote {d/'config_d_hydro.xml'}")
    print("needs beside it:", f"{args.prefix}.grd/.dep/.enc + .wnd + .tem + .eva")


if __name__ == "__main__":
    main()
