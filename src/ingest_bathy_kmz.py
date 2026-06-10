"""
ingest_bathy_kmz.py -- turn a lake's per-depth KMZ contour layers into a
(lon, lat, depth) point cloud + summary, ready for grid/.dep building.

Each KMZ is one depth contour (a KML LineString of WGS84 lon,lat). The depth is
encoded in the filename, two conventions seen in the corpus:
  * explicit:  "...layer_99m (0m depth).kmz"      -> depth = 0
  * elevation: "Nth_layer_<elev>m.kmz"            -> depth = (max elev) - elev
We prefer the explicit "(Xm depth)" tag; otherwise derive from the elevation
sequence within the lake.

Usage:
  python src/ingest_bathy_kmz.py --root bathymetry/raw --out bathymetry/points
  python src/ingest_bathy_kmz.py --root bathymetry/raw --inventory-only
"""
from __future__ import annotations
import argparse, re, zipfile
from pathlib import Path
import numpy as np

DEPTH_PAREN = re.compile(r"\((\d+(?:\.\d+)?)\s*m?\s*depth\)", re.I)
ELEV = re.compile(r"_(\d+(?:\.\d+)?)\s*m", re.I)
COORD = re.compile(r"<coordinates>(.*?)</coordinates>", re.S | re.I)


def kml_from_kmz(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.lower().endswith(".kml"):
                return z.read(n).decode("utf-8", "ignore")
    return ""


def coords_of(kml: str):
    pts = []
    for block in COORD.findall(kml):
        for tok in block.split():
            parts = tok.split(",")
            if len(parts) >= 2:
                try:
                    pts.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    pass
    return pts


def layer_depth(fname: str, max_elev: float | None):
    m = DEPTH_PAREN.search(fname)
    if m:
        return float(m.group(1))
    m = ELEV.search(fname)
    if m and max_elev is not None:
        return max_elev - float(m.group(1))
    return None


def lake_elevs(kmzs):
    """Max elevation token across a lake's filenames (for the elevation convention)."""
    elevs = []
    for k in kmzs:
        if DEPTH_PAREN.search(k.name):
            return None  # explicit-depth lake; no elevation derivation needed
        m = ELEV.search(k.name)
        if m:
            elevs.append(float(m.group(1)))
    return max(elevs) if elevs else None


def process_lake(folder: Path):
    kmzs = sorted(folder.glob("*.kmz"))
    if not kmzs:
        return None
    max_elev = lake_elevs(kmzs)
    rows = []
    for k in kmzs:
        d = layer_depth(k.name, max_elev)
        if d is None:
            continue
        for lon, lat in coords_of(kml_from_kmz(k)):
            rows.append((lon, lat, d))
    if not rows:
        return None
    arr = np.array(rows, dtype="f8")
    lon, lat, dep = arr[:, 0], arr[:, 1], arr[:, 2]
    # rough planar area of the surface (0 m) contour bbox, km^2 (cos-lat corrected)
    latm = np.deg2rad(lat.mean())
    dx = (lon.max() - lon.min()) * 111.32 * np.cos(latm)
    dy = (lat.max() - lat.min()) * 110.57
    return dict(
        lake=folder.name, n_layers=len(kmzs), n_pts=len(rows),
        lon_min=lon.min(), lon_max=lon.max(), lat_min=lat.min(), lat_max=lat.max(),
        lon_c=lon.mean(), lat_c=lat.mean(),
        max_depth=dep.max(), bbox_km=f"{dx:.1f}x{dy:.1f}", points=arr,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="dir containing per-lake folders")
    ap.add_argument("--out", default=None, help="dir to write <lake>_points.csv")
    ap.add_argument("--inventory-only", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    # find the actual lake folders (dirs that contain kmz)
    lake_dirs = sorted({p.parent for p in root.rglob("*.kmz")})
    print(f"{'lake':32s} {'layers':>6} {'pts':>8} {'maxdep':>7}  {'bbox(km)':>12}  centroid")
    print("-" * 100)
    results = []
    for d in lake_dirs:
        r = process_lake(d)
        if not r:
            continue
        results.append(r)
        print(f"{r['lake']:32s} {r['n_layers']:6d} {r['n_pts']:8d} "
              f"{r['max_depth']:6.1f}m {r['bbox_km']:>12}  "
              f"{r['lon_c']:.3f},{r['lat_c']:.3f}")
        if args.out and not args.inventory_only:
            od = Path(args.out); od.mkdir(parents=True, exist_ok=True)
            np.savetxt(od / f"{r['lake']}_points.csv", r["points"],
                       delimiter=",", header="lon,lat,depth_m", comments="")
    print("-" * 100)
    print(f"{len(results)} lakes with usable KMZ bathymetry")

    if args.out:
        od = Path(args.out); od.mkdir(parents=True, exist_ok=True)
        cols = ["lake", "n_layers", "n_pts", "max_depth", "bbox_km",
                "lon_c", "lat_c", "lon_min", "lon_max", "lat_min", "lat_max"]
        with open(od.parent / "inventory.csv", "w", encoding="utf-8") as fh:
            fh.write(",".join(cols) + "\n")
            for r in results:
                fh.write(",".join(str(r[c]) for c in cols) + "\n")
        print(f"wrote {od.parent / 'inventory.csv'}")


if __name__ == "__main__":
    main()
