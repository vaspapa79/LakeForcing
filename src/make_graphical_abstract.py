"""
make_graphical_abstract.py -- Elsevier graphical abstract for LakeForcing.
Plate-assembled from the paper's own data: stage 1 is the global lake map (real
paper figure); stages 2-4 are clean single panels rendered directly from the
released forcing/trajectory NetCDFs (no titles, colorbars or neighbouring panels
to clip). Each stage sits, undistorted, inside a titled rounded box; arrows link
the stages; a results banner sits below. >=300 dpi.

  python src/make_graphical_abstract.py
"""
import json
from pathlib import Path
import numpy as np
import xarray as xr
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
DOCS, OUT = ROOT / "docs", ROOT / "output"
PAN, CORE, ARR, PANE = "#ffffff", "#c0392b", "#23456b", "#c4d2e2"
FIGW, FIGH = 10.0, 4.7


def _crop_wet(ax, lon, lat, wet):
    cc = np.where(wet.any(axis=0))[0]; rr = np.where(wet.any(axis=1))[0]
    if cc.size and rr.size:
        px = max((lon[cc[-1]] - lon[cc[0]]) * 0.03, 1e-6)
        py = max((lat[rr[-1]] - lat[rr[0]]) * 0.03, 1e-6)
        ax.set_xlim(lon[cc[0]] - px, lon[cc[-1]] + px)
        ax.set_ylim(lat[rr[0]] - py, lat[rr[-1]] + py)


def draw_current(ax, prefix):
    ds = xr.open_dataset(OUT / f"{prefix}_forcing.nc")
    u = np.nanmean(ds["u"].isel(depth=0).values, axis=0)
    v = np.nanmean(ds["v"].isel(depth=0).values, axis=0)
    spd = np.hypot(u, v); fin = spd[np.isfinite(spd)]
    vmax = np.nanpercentile(fin, 97) if fin.size else 0.05
    ax.set_facecolor("#e9e9e9")
    cmap = plt.get_cmap("turbo").copy(); cmap.set_bad(alpha=0)
    ax.pcolormesh(ds.lon, ds.lat, np.ma.masked_invalid(spd), cmap=cmap,
                  vmin=0, vmax=max(vmax, 1e-3), shading="auto")
    _crop_wet(ax, ds.lon.values, ds.lat.values, np.isfinite(spd))
    ax.set_aspect("equal"); ax.set_anchor("C"); ax.set_xticks([]); ax.set_yticks([])
    ds.close()


def draw_section(ax, prefix):
    ds = xr.open_dataset(OUT / f"{prefix}_forcing.nc")
    temp = ds["temp"].values                       # (time, depth, lat, lon)
    valid = np.isfinite(temp[0]).sum(axis=0)
    jy, jx = np.unravel_index(np.argmax(valid), valid.shape)
    sec = temp[:, :, jy, jx]                        # (time, depth)
    z = ds["depth"].values
    hours = np.arange(temp.shape[0])
    cmap = plt.get_cmap("inferno").copy(); cmap.set_bad("#f3f3f3")
    ax.pcolormesh(hours, z, np.ma.masked_invalid(sec).T, cmap=cmap, shading="auto")
    kz = np.where(np.isfinite(sec).any(axis=0))[0]
    if kz.size:
        ax.set_ylim(z[kz[-1]], 0)
    ax.set_aspect("auto"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#888"); s.set_linewidth(0.6)
    ds.close()


def draw_traj(ax, prefix):
    ds = xr.open_dataset(OUT / f"{prefix}_forcing.nc")
    u = np.nanmean(ds["u"].isel(depth=0).values, axis=0)
    v = np.nanmean(ds["v"].isel(depth=0).values, axis=0)
    spd = np.hypot(u, v); fin = spd[np.isfinite(spd)]
    vmax = np.nanpercentile(fin, 97) if fin.size else 0.05
    ax.set_facecolor("#e9e9e9")
    cmap = plt.get_cmap("turbo").copy(); cmap.set_bad(alpha=0)
    ax.pcolormesh(ds.lon, ds.lat, np.ma.masked_invalid(spd), cmap=cmap,
                  vmin=0, vmax=max(vmax, 1e-3), shading="auto")
    tr = xr.open_dataset(OUT / f"{prefix}_trajectory.nc")
    lon, lat = tr["lon"].values, tr["lat"].values
    for i in range(0, lon.shape[0], max(1, lon.shape[0] // 60)):
        ax.plot(lon[i], lat[i], "-", color="black", lw=0.35, alpha=0.55)
    ax.plot(lon[::20, -1], lat[::20, -1], ".", color="#ff2d2d", ms=2.0)
    sd = OUT / f"{prefix}_seed.json"
    if sd.exists():
        s = json.loads(sd.read_text())
        ax.plot(s["lon"], s["lat"], "*", color="yellow", ms=13, mec="black", mew=0.7)
    tr.close()
    _crop_wet(ax, ds.lon.values, ds.lat.values, np.isfinite(spd))
    ax.set_aspect("equal"); ax.set_anchor("C"); ax.set_xticks([]); ax.set_yticks([])
    ds.close()


# stage: (drawer, title, edge colour)
STAGES = [
    ("map",   "Open global data\nbathymetry + ERA5", PANE),
    ("current", "Coupled Delft3D\nFLOW + WAVE (SWAN)", PANE),
    ("section", "σ-to-z CF-NetCDF\nexport", CORE),
    ("traj",  "OpenDrift\nparticle transport", PANE),
]


def main():
    fig = plt.figure(figsize=(FIGW, FIGH))
    bg = fig.add_axes([0, 0, 1, 1]); bg.set_xlim(0, 1); bg.set_ylim(0, 1); bg.axis("off")
    bg.text(0.5, 0.955, "LakeForcing: from open data to lake transport "
            "forcing", ha="center", va="center", fontsize=14.5, fontweight="bold",
            color="#15233a")

    L, gap = 0.018, 0.045
    bw = (1 - 2 * L - 3 * gap) / 4
    yb, yt = 0.300, 0.855
    h = yt - yb
    ymid = (yb + yt) / 2
    lake_map = np.asarray(Image.open(DOCS / "figure_lake_map.png").convert("RGB"))

    for i, (kind, title, ec) in enumerate(STAGES):
        x0 = L + i * (bw + gap)
        bg.add_patch(FancyBboxPatch((x0 + 0.004, yb - 0.008), bw, h,
                     boxstyle="round,pad=0.004,rounding_size=0.018", fc="#000000",
                     ec="none", alpha=0.08, zorder=1))
        bg.add_patch(FancyBboxPatch((x0, yb), bw, h,
                     boxstyle="round,pad=0.004,rounding_size=0.018", fc=PAN, ec=ec,
                     lw=2.4 if ec == CORE else 1.4, zorder=2))
        bg.text(x0 + bw / 2, yt - 0.030, title, ha="center", va="top", fontsize=8.7,
                fontweight="bold", color=CORE if ec == CORE else "#1a1a1a", zorder=4)
        area = [x0 + 0.012, yb + 0.030, bw - 0.024, (yt - 0.120) - (yb + 0.030)]
        ax = fig.add_axes(area, zorder=3)
        if kind == "map":
            ax.imshow(lake_map, aspect="equal"); ax.set_anchor("C"); ax.axis("off")
        elif kind == "current":
            draw_current(ax, "polyfytos")
        elif kind == "section":
            draw_section(ax, "erken")
        else:
            draw_traj(ax, "poyang")

    for i in range(3):
        xa = L + i * (bw + gap) + bw
        xb = L + (i + 1) * (bw + gap)
        a = FancyArrowPatch((xa + 0.003, ymid), (xb - 0.003, ymid), arrowstyle="-|>",
                            mutation_scale=17, lw=2.6, color=ARR, zorder=6)
        a.set_path_effects([pe.withStroke(linewidth=4.5, foreground="white")])
        bg.add_patch(a)

    bg.add_patch(FancyBboxPatch((L, 0.045), 1 - 2 * L, 0.205,
                 boxstyle="round,pad=0.004,rounding_size=0.02", fc="#eef3f9",
                 ec="#c4d2e2", lw=1.3, zorder=1))
    bg.text(0.5, 0.193, "One unmodified pipeline — demonstrated on 12 lakes across "
            "all inhabited continents (36°S–60°N)", ha="center", va="center",
            fontsize=10.8, fontweight="bold", color="#15233a", zorder=4)
    bg.text(0.5, 0.100, "36-h surface drift 0.34–3.7 km   ·   benchmarked vs an "
            "expert model (0.85 °C, 1.5 cm s⁻¹) and satellite LSWT", ha="center",
            va="center", fontsize=9.6, color="#333", zorder=4)

    for out in (DOCS / "graphical_abstract.png", ROOT / "paper" / "GraphicalAbstract.png"):
        fig.savefig(out, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.05)
        print("wrote", out)
    plt.close(fig)


if __name__ == "__main__":
    main()
