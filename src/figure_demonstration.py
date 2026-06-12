"""
figure_demonstration.py -- EMS "demonstration across cases" figure: one panel per
lake showing the surface current speed + 36 h particle trajectories, arranged along
the diversity gradient. Reads output/<lake>_forcing.nc + <lake>_trajectory.nc.

  python src/figure_demonstration.py
"""
from pathlib import Path
import json
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift/output")

# ordered along a diversity gradient, with a short descriptor
LAKES = [
    ("lagdo",     "Lagdo, Cameroon\ntropical reservoir, 8N"),
    ("trasimeno", "Trasimeno, Italy\nshallow, 43N"),
    ("balaton",   "Balaton, Hungary\nshallow, 47N"),
    ("bornos",    "Bornos, Spain\nreservoir"),
    ("mead",      "Lake Mead, USA\nreservoir"),
    ("polyfytos", "Polyfytos, Greece\nreservoir"),
    ("rotsee",    "Rotsee, Switzerland\ndeep, small"),
    ("erken",     "Erken, Sweden\nboreal, 60N"),
    ("poyang",    "Poyang, China\nshallow, 29N"),
    ("sea_of_galilee", "Sea of Galilee\nIsrael, 33N"),
    ("eucumbene", "Eucumbene, Australia\nreservoir, 36S"),
    ("nova_ponte", "Nova Ponte, Brazil\nreservoir, 19S"),
]


def panel(ax, prefix, label):
    f = OUT / f"{prefix}_forcing.nc"
    t = OUT / f"{prefix}_trajectory.nc"
    if not f.exists():
        ax.text(0.5, 0.5, f"{prefix}\n(pending)", ha="center", va="center")
        ax.axis("off"); return
    ds = xr.open_dataset(f)
    # time-mean surface current speed brings out the circulation pattern
    u = np.nanmean(ds["u"].isel(depth=0).values, axis=0)
    v = np.nanmean(ds["v"].isel(depth=0).values, axis=0)
    spd = np.sqrt(u**2 + v**2)
    finite = spd[np.isfinite(spd)]
    vmax = np.nanpercentile(finite, 97) if finite.size else 0.05
    # paint land/dry (NaN) as a neutral grey so panels never read as blank white
    ax.set_facecolor("#e8e8e8")
    cmap = plt.get_cmap("turbo").copy()
    cmap.set_bad(alpha=0.0)                       # NaN -> show grey facecolor
    spd_m = np.ma.masked_invalid(spd)
    pm = ax.pcolormesh(ds.lon, ds.lat, spd_m, cmap=cmap,
                       vmin=0, vmax=max(vmax, 1e-3), shading="auto")
    # crop tightly to the wet bounding box so the lake fills the panel
    lon, lat = ds.lon.values, ds.lat.values
    wet = np.isfinite(spd)
    if wet.any():
        cc = np.where(wet.any(axis=0))[0]; rr = np.where(wet.any(axis=1))[0]
        px = max((lon[cc[-1]] - lon[cc[0]]) * 0.02, 1e-6)
        py = max((lat[rr[-1]] - lat[rr[0]]) * 0.02, 1e-6)
        ax.set_xlim(lon[cc[0]] - px, lon[cc[-1]] + px)
        ax.set_ylim(lat[rr[0]] - py, lat[rr[-1]] + py)
    if t.exists():
        tr = xr.open_dataset(t)
        lon, lat = tr["lon"].values, tr["lat"].values
        for i in range(0, lon.shape[0], max(1, lon.shape[0] // 60)):
            ax.plot(lon[i], lat[i], "-", color="black", lw=0.3, alpha=0.55)
        ax.plot(lon[::20, -1], lat[::20, -1], ".", color="#ff2d2d", ms=1.6)
        # mark the TRUE release centre (sidecar), not a single scattered
        # particle (lon[0,0]) which can sit on a dry cell in small lakes
        seed = OUT / f"{prefix}_seed.json"
        if seed.exists():
            s = json.loads(seed.read_text())
            ax.plot(s["lon"], s["lat"], "*", color="yellow", ms=11,
                    mec="black", mew=0.6)
        else:
            ax.plot(lon[0, 0], lat[0, 0], "*", color="yellow", ms=11,
                    mec="black", mew=0.6)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(label, fontsize=12)
    return pm


def main():
    n = len(LAKES); ncol = 4; nrow = (n + ncol - 1) // ncol
    fig, axs = plt.subplots(nrow, ncol, figsize=(3.6 * ncol, 3.0 * nrow))
    # pack panels tightly: equal aspect already shrinks each axes within its
    # cell, so minimise the cell gaps to recover that space for the lakes
    fig.subplots_adjust(left=0.012, right=0.988, top=0.875, bottom=0.012,
                        wspace=0.04, hspace=0.20)
    pm = None
    for ax, (p, lab) in zip(np.ravel(axs), LAKES):
        r = panel(ax, p, lab)
        if r is not None:
            pm = r
    for ax in np.ravel(axs)[n:]:
        ax.axis("off")
    fig.suptitle("Lake forcing pipeline demonstrated across twelve lakes\n"
                 "colour = mean surface current speed (per-lake scale, blue=slow, red=fast); "
                 "grey = land; black lines = 36 h trajectories; ★ release, • endpoints",
                 fontsize=14, y=0.99)
    fig.savefig(OUT / "figure_demonstration.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    print("wrote", OUT / "figure_demonstration.png")


if __name__ == "__main__":
    main()
