"""
batch_build_grids.py -- build Delft3D-4 grids for every lake in the corpus
(KMZ point clouds + DAHITI/GEBCO rasters), auto-picking resolution per lake,
and emit a QC contact sheet + inventory. Surfaces bad bathymetry (flat fills,
partial coverage) before any Delft3D run. No engine / no licence.

  python src/batch_build_grids.py
  python src/batch_build_grids.py --only rotsee mead baikal
"""
import argparse, json, traceback
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import build_grid as bg

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
POINTS = ROOT / "bathymetry/points"
DAHITI = ROOT / "bathymetry/dahiti"
GEBCO = ROOT / "bathymetry/gebco"
OUT = ROOT / "models"
TARGET_CELLS = 120          # aim ~120 cells across the long axis
RES_MIN, RES_MAX = 15.0, 1000.0

DAHITI_NAMES = {  # id -> short key
    "1374": "dead_sea", "13705": "sea_of_galilee", "118": "mosul",
    "204": "mead", "71": "salton_sea", "11112": "fort_peck",
    "11521": "enriquillo", "228": "poyang", "233": "siling_co",
    "13610": "naivasha", "13220": "nakuru", "1472": "lagdo",
    "64": "eucumbene", "10341": "forggensee", "10351": "nova_ponte",
    "4475": "tunas_grandes", "606": "massingir", "11576": "gilgel_gibe",
}


def pick_res(lon, lat):
    epsg = bg.local_utm_epsg(float(np.mean(lon)), float(np.mean(lat)))
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    x, y = tr.transform(lon, lat)
    span = max(np.ptp(x), np.ptp(y))
    return float(np.clip(span / TARGET_CELLS, RES_MIN, RES_MAX))


def _clean_key(stem):
    import re
    return re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")


def discover():
    jobs = []
    for c in sorted(POINTS.glob("*_points.csv")):
        key = _clean_key(c.name.replace("_points.csv", ""))   # unique per lake
        jobs.append(("points", key, c))
    for t in sorted(DAHITI.glob("dahiti_*_bathymetry.tif")):
        tid = t.stem.split("_")[1]
        jobs.append(("raster", DAHITI_NAMES.get(tid, f"dahiti_{tid}"), t))
    for t in sorted(GEBCO.glob("gebco_*.tif")):
        jobs.append(("raster", t.stem.replace("gebco_", ""), t))
    return jobs


# Known water-surface elevation (m a.s.l.) for rasters whose bbox includes land
# beyond the lake, where the 99th-pct auto-estimate picks terrain not water.
# (DAHITI tifs are tightly clipped, so they don't need this; GEBCO subsets do.)
SURFACE_LEVELS = {"baikal": 456.0, "superior": 183.0}


def build_one(kind, key, src):
    if kind == "points":
        lon, lat, depth = bg.load_points(src)
    else:
        lon, lat, depth = bg.load_raster(src, SURFACE_LEVELS.get(key))
    res = pick_res(lon, lat)
    epsg, GX, GY, d = bg.build_nodes(lon, lat, depth, res)
    outdir = OUT / key; outdir.mkdir(parents=True, exist_ok=True)
    pre = outdir / key
    Mp, Np = bg.write_grd(f"{pre}.grd", GX, GY)
    bg.write_dep(f"{pre}.dep", d)
    bg.write_enc(f"{pre}.enc", Mp, Np)
    wet = d > 0
    meta = dict(lake=key, source=kind, epsg=epsg, res_m=round(res, 1),
                grd=[Mp, Np], mdf_MNKmax=[Mp + 1, Np + 1],
                wet_nodes=int(wet.sum()), total_nodes=int(d.size),
                max_depth_m=round(float(d[wet].max()), 1) if wet.any() else 0.0,
                wet_frac=round(float(wet.mean()), 3))
    (Path(f"{pre}_grid.json")).write_text(json.dumps(meta, indent=2))
    meta["_GX"], meta["_GY"], meta["_D"] = GX, GY, np.where(wet, d, np.nan)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    jobs = discover()
    if args.only:
        sel = set(s.lower() for s in args.only)
        jobs = [j for j in jobs if j[1] in sel]

    metas, panels = [], []
    for kind, key, src in jobs:
        try:
            m = build_one(kind, key, src)
            panels.append(m)
            flag = "  ⚠ FLAT?" if m["max_depth_m"] < 0.5 else ""
            print(f"{key:18s} {kind:6s} {m['grd'][0]:3d}x{m['grd'][1]:<3d} "
                  f"res={m['res_m']:6.1f}m  wet={m['wet_nodes']:5d} "
                  f"maxdep={m['max_depth_m']:6.1f}m{flag}")
            metas.append({k: v for k, v in m.items() if not k.startswith("_")})
        except Exception as e:
            print(f"{key:18s} FAILED: {e}")
            traceback.print_exc()

    # inventory csv
    if metas:
        cols = ["lake", "source", "epsg", "res_m", "grd", "mdf_MNKmax",
                "wet_nodes", "wet_frac", "max_depth_m"]
        with open(OUT / "grid_inventory.csv", "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for m in metas:
                fh.write(",".join(str(m[c]).replace(",", " ") for c in cols) + "\n")
        print(f"\nwrote {OUT/'grid_inventory.csv'}")

    # contact sheet
    n = len(panels)
    if n:
        ncol = 5; nrow = (n + ncol - 1) // ncol
        fig, axs = plt.subplots(nrow, ncol, figsize=(3 * ncol, 2.6 * nrow))
        for ax, m in zip(np.ravel(axs), panels):
            ax.pcolormesh(m["_GX"], m["_GY"], m["_D"], cmap="viridis_r", shading="auto")
            ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
            flag = " ⚠" if m["max_depth_m"] < 0.5 else ""
            ax.set_title(f"{m['lake']}{flag}\n{m['max_depth_m']:.0f}m {m['grd'][0]}x{m['grd'][1]}",
                         fontsize=8)
        for ax in np.ravel(axs)[n:]:
            ax.axis("off")
        fig.suptitle(f"Lake grid QC contact sheet ({n} lakes)", fontsize=12)
        fig.tight_layout()
        fig.savefig(OUT / "grid_qc_contact_sheet.png", dpi=100)
        print(f"wrote {OUT/'grid_qc_contact_sheet.png'}")


if __name__ == "__main__":
    main()
