"""
gebco_subset.py -- extract a lake bounding-box from the global GEBCO_2024 grid
via a cloud-optimized-GeoTIFF windowed read (GDAL /vsicurl/), WITHOUT downloading
the ~7 GB global file. Values = bed/terrain ELEVATION in metres (sea-level datum);
for a lake, depth = surface_level - elevation (handled in 02_build_grid.py).

No auth required. Needs rasterio (present in the `plastic` env).

Usage:
  python src/gebco_subset.py --name baikal --bbox 103.5 51.4 110.3 55.9
  python src/gebco_subset.py --name geneva --bbox 6.10 46.20 6.95 46.55
"""
import argparse
from pathlib import Path
import rasterio
from rasterio.windows import from_bounds

COG = "/vsicurl/https://data.source.coop/alexgleith/gebco-2024/GEBCO_2024.tif"
OUT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift/bathymetry/gebco")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--bbox", nargs=4, type=float, required=True,
                    metavar=("W", "S", "E", "N"), help="lon/lat bounds")
    ap.add_argument("--cog", default=COG)
    args = ap.parse_args()
    w, s, e, n = args.bbox
    OUT.mkdir(parents=True, exist_ok=True)

    # GDAL/curl tuning for a responsive windowed read over HTTP
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                      VSI_CACHE="TRUE"):
        with rasterio.open(args.cog) as src:
            win = from_bounds(w, s, e, n, transform=src.transform)
            data = src.read(1, window=win)
            tr = src.window_transform(win)
            prof = src.profile.copy()
            prof.update(height=data.shape[0], width=data.shape[1],
                        transform=tr, compress="deflate")
    out = OUT / f"gebco_{args.name}.tif"
    with rasterio.open(out, "w", **prof) as dst:
        dst.write(data, 1)

    import numpy as np
    v = data[np.isfinite(data)]
    print(f"wrote {out}")
    print(f"  shape={data.shape}  elev[min..max]={v.min():.0f}..{v.max():.0f} m  "
          f"(deepest bed {v.min():.0f} m a.s.l.)")


if __name__ == "__main__":
    main()
