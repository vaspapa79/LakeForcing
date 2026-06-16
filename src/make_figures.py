"""
make_figures.py -- generate the manuscript's conceptual + analysis figures:
  figure_architecture.png      professional multi-stage pipeline diagram
  figure_sigma_schematic.png   sigma-layer -> z-level coupling concept
  figure_lake_map.png          global distribution of the 8 demonstration lakes
  figure_drift_scatter.png     36 h drift vs lake mean depth (physical gradient)
  figure_forcing_example.png   actual forcing fields for one lake (currents/T/Hs)

Run with the OpenDrift/cartopy env:
  C:/Users/vaspapa/miniconda3/envs/plastic/python.exe src/make_figures.py
"""
from pathlib import Path
import json
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
from matplotlib.lines import Line2D

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
OUT = ROOT / "output"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

# lake metadata (lon, lat, type, max depth m, mean depth m approx, drift m)
LAKES = {
    "lagdo":     dict(lon=13.92, lat=8.79,  type="reservoir", dmax=9,  dmean=4.5, drift=2439, name="Lagdo"),
    "bornos":    dict(lon=-5.70, lat=36.81, type="reservoir", dmax=20, dmean=8,   drift=1337, name="Bornos"),
    "mead":      dict(lon=-114.37,lat=36.23,type="reservoir", dmax=40, dmean=20,  drift=2933, name="Mead"),
    "polyfytos": dict(lon=21.94, lat=40.21, type="reservoir", dmax=80, dmean=30,  drift=1743, name="Polyfytos"),
    "trasimeno": dict(lon=12.12, lat=43.13, type="natural",   dmax=7,  dmean=4.7, drift=3419, name="Trasimeno"),
    "balaton":   dict(lon=17.73, lat=46.83, type="natural",   dmax=9,  dmean=3.2, drift=3250, name="Balaton"),
    "rotsee":    dict(lon=8.31,  lat=47.07, type="natural",   dmax=16, dmean=9,   drift=341,  name="Rotsee"),
    "erken":     dict(lon=18.58, lat=59.84, type="natural",   dmax=20, dmean=9,   drift=2033, name="Erken"),
    "poyang":    dict(lon=116.25,lat=29.10, type="natural",   dmax=6,  dmean=3,   drift=3695, name="Poyang"),
    "sea_of_galilee": dict(lon=35.59, lat=32.82, type="natural", dmax=6, dmean=3, drift=3506, name="Galilee"),
    "eucumbene": dict(lon=148.62,lat=-36.10,type="reservoir", dmax=38, dmean=18,  drift=3166, name="Eucumbene"),
    "nova_ponte":dict(lon=-46.40,lat=-19.13,type="reservoir", dmax=23, dmean=11,  drift=2881, name="Nova Ponte"),
}

BLUE, GREEN, ORANGE, RED, PURPLE = "#2c6fbb", "#2e8b57", "#e08214", "#c0392b", "#6a3d9a"


# --------------------------------------------------------------------------- #
def fig_architecture():
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Polygon,
                                    Circle, Ellipse, Wedge)
    fig, ax = plt.subplots(figsize=(13.6, 5.2))   # ~132:50.5 keeps circles round
    ax.set_xlim(0, 132); ax.set_ylim(0, 64); ax.axis("off")

    SKY1, SKY2 = "#eaf4fb", "#cfe7f7"
    WAT_T, WAT_D = "#aedaf2", "#1f6fa8"
    SAND, SANDD = "#e6d196", "#c19a55"
    SUN = "#f7c948"
    CLOUD = "#ffffff"
    LAND, LANDE = "#bfe0a8", "#86b769"
    PAN, PANE = "#fbfcfe", "#cdd7e3"
    CORE = "#c0392b"
    PARTS = ["#e8553a", "#f29d3d", "#7d4fb0", "#2e9e8f", "#d64550", "#3a7ec0"]

    def vgrad(x0, x1, y0, y1, ctop, cbot, clip, z=1.2):
        cmap = LinearSegmentedColormap.from_list("g", [cbot, ctop])
        im = ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1),
                       extent=[x0, x1, y0, y1], origin="lower", aspect="auto",
                       cmap=cmap, zorder=z)
        im.set_clip_path(clip)
        return im

    def panel(x, y, w, h, ec=PANE, lw=1.2):
        ax.add_patch(FancyBboxPatch((x + 0.5, y - 0.7), w, h,
                     boxstyle="round,pad=0.2,rounding_size=2.4", fc="#000000",
                     ec="none", alpha=0.09, zorder=0))           # soft shadow
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=2.4",
                           fc=PAN, ec=ec, lw=lw, zorder=1)
        ax.add_patch(p)
        return p

    def caption(cx, y, title, sub=None, color="#222"):
        ax.text(cx, y, title, ha="center", va="top", fontsize=13.5,
                fontweight="bold", color=color, zorder=6)
        if sub:
            ax.text(cx, y - 3.1, sub, ha="center", va="top", fontsize=10,
                    style="italic", color="#555", zorder=6)

    ax.text(66, 54.8, "The LakeForcing-OpenDrift pipeline", ha="center",
            fontsize=21, fontweight="bold", zorder=6)

    # ----- panels (tight gaps) -----
    P1 = panel(2, 12, 31, 40)
    P2 = panel(35.5, 12, 41, 40)
    P3 = panel(79.5, 12, 19.5, 40, ec=CORE, lw=2.6)
    P4 = panel(101.5, 12, 28.5, 40)

    # ============ Scene 1: open global data (globe + sky) ============
    gx, gy, gr = 16, 36, 9
    ax.add_patch(Circle((gx, gy), gr, fc="#bfe3f7", ec="#3a7ca5", lw=1.3, zorder=2))
    # continents
    for poly in ([(13,42),(18,43),(20,40),(16,38),(12,39)],
                 [(11,33),(15,32),(17,29),(12,28),(9,31)],
                 [(19,35),(22,34),(23,31),(20,32)]):
        ax.add_patch(Polygon(poly, closed=True, fc=LAND, ec=LANDE, lw=0.8, zorder=3))
    for e in (0.45, 0.78):                      # meridians
        ax.add_patch(Ellipse((gx, gy), gr*2*e, gr*2, fc="none", ec="#7fb4d2",
                     lw=0.6, zorder=3))
    ax.add_patch(Ellipse((gx, gy), gr*2, gr*0.9, fc="none", ec="#7fb4d2",
                 lw=0.6, zorder=3))            # equator
    # highlighted lake on globe
    ax.add_patch(Circle((18.4, 38.6), 1.0, fc=CORE, ec="white", lw=1.0, zorder=4))
    ax.add_patch(Circle((18.4, 38.6), 2.3, fc="none", ec=CORE, lw=1.2, zorder=4))
    # ERA5 sky: sun + cloud + wind, lower part of panel
    ax.add_patch(Circle((10, 20), 2.6, fc=SUN, ec="#e0a800", lw=0.8, zorder=2))
    for a in range(0, 360, 45):
        rad = np.deg2rad(a)
        ax.plot([10+3.1*np.cos(rad), 10+4.3*np.cos(rad)],
                [20+3.1*np.sin(rad), 20+4.3*np.sin(rad)], color="#e0a800",
                lw=1.1, zorder=2)
    for (cx, cy, s) in [(17, 21, 1.0), (19.5, 19.5, 0.8)]:
        for dx in (-2.2, 0, 2.4):
            ax.add_patch(Circle((cx+dx*s, cy), 2.0*s, fc=CLOUD, ec="#cfd9e3",
                         lw=0.7, zorder=3))
        ax.add_patch(FancyBboxPatch((cx-3.2*s, cy-2.0*s), 6.6*s, 2.2*s,
                     boxstyle="round,pad=0.1,rounding_size=1.0", fc=CLOUD,
                     ec="#cfd9e3", lw=0.7, zorder=3))
    for wy in (15.5, 17.0):
        ax.add_patch(FancyArrowPatch((6, wy), (26, wy+0.4), arrowstyle="-|>",
                     mutation_scale=10, lw=1.3, color="#5b9bd5",
                     connectionstyle="arc3,rad=0.18", zorder=4))
    caption(16, 10.5, "Open global data",
            "HydroLAKES · GLOBathy · DAHITI · ERA5")

    # ============ Scene 2 (hero): coupled Delft3D lake basin ============
    x = np.linspace(36, 75, 120)
    bed = 17 + 9*((x-55.5)/19.5)**2            # basin: high edges, low centre
    bed = np.clip(bed, 17, 30)
    surf = 41 + 0.6*np.sin((x-36)/2.4)         # wavy surface
    # sky gradient (clipped to panel)
    vgrad(35.5, 76.5, 12, 52, SKY1, SKY2, P2, z=1.1)
    # water body polygon (surface over bed)
    wx = np.r_[x, x[::-1]]
    wy = np.r_[surf, bed[::-1]]
    water = Polygon(np.c_[wx, wy], closed=True, fc="none", ec="none", zorder=1.3)
    ax.add_patch(water)
    vgrad(36, 75, 16, 42, WAT_T, WAT_D, water, z=1.4)
    # bed (sand)
    bx = np.r_[x, x[::-1]]
    by = np.r_[bed, np.full_like(bed, 12.5)[::-1]]
    sand = Polygon(np.c_[bx, by], closed=True, fc=SAND, ec=SANDD, lw=1.0, zorder=1.6)
    ax.add_patch(sand)
    # sigma layers following the bed
    for s in np.linspace(0.12, 0.92, 6):
        zl = surf - s*(surf-bed)
        ax.plot(x, zl, color="#1d4e74", lw=0.8, alpha=0.7, zorder=2)
    # surface line + little waves
    ax.plot(x, surf, color="#0d3b5c", lw=1.6, zorder=2.4)
    for xc in np.linspace(39, 72, 9):
        ax.add_patch(Wedge((xc, np.interp(xc, x, surf)+0.15), 0.7, 200, 340,
                     width=0.25, fc="white", ec="#0d3b5c", lw=0.4, zorder=2.5))
    # current arrows inside water
    for cy in (35, 28):
        ax.add_patch(FancyArrowPatch((42, cy), (69, cy), arrowstyle="-|>",
                     mutation_scale=11, lw=2.0, color="#ffffff", alpha=0.85,
                     connectionstyle="arc3,rad=0.04", zorder=2.6))
    # sun + cloud + wind above the lake
    ax.add_patch(Circle((41, 49), 2.2, fc=SUN, ec="#e0a800", lw=0.8, zorder=2))
    for dx in (-2, 0.4, 2.6):
        ax.add_patch(Circle((49+dx, 48.5), 1.9, fc=CLOUD, ec="#cfd9e3", lw=0.7, zorder=2.2))
    for wy in (45.5, 47.2):
        ax.add_patch(FancyArrowPatch((55, wy), (71, wy+0.5), arrowstyle="-|>",
                     mutation_scale=11, lw=1.6, color="#3f7fb0",
                     connectionstyle="arc3,rad=0.2", zorder=3))
    ax.text(55.5, 51.2, "wind · heat · waves", ha="center", fontsize=10,
            style="italic", color="#33576e", zorder=4)
    caption(55.5, 10.5, "Coupled Delft3D-FLOW + WAVE",
            "automated closed-lake setup · σ-layers")

    # ============ Scene 3: sigma -> z coupling (the core) ============
    # mini terrain-following layers (left)
    xs = np.linspace(82, 88, 40)
    bs = 24 + 4*((xs-85)/3)**2
    ss = np.full_like(xs, 38)
    for s in np.linspace(0.15, 0.9, 4):
        ax.plot(xs, ss - s*(ss-bs), color="#1d4e74", lw=0.8, zorder=2)
    ax.plot(xs, ss, color="#0d3b5c", lw=1.3, zorder=2)
    ax.plot(xs, bs, color=SANDD, lw=1.3, zorder=2)
    ax.text(85, 41.0, "σ-layers", ha="center", fontsize=12.8, color="#1d4e74", zorder=3)
    # transform arrow
    ax.add_patch(FancyArrowPatch((88.6, 31), (91.2, 31), arrowstyle="-|>",
                 mutation_scale=14, lw=2.2, color=CORE, zorder=4))
    # isometric z-level slabs (right)
    cx0, cyt, w, sk, d, th, gap = 91.5, 38, 5.4, 2.0, 1.3, 1.1, 2.3
    zcmap = LinearSegmentedColormap.from_list("z", ["#2f6f9f", "#7fb24a", "#f2a33d"])
    for i in range(6):
        yt = cyt - i*gap
        col = zcmap(i/5)
        ax.add_patch(Polygon([(cx0, yt), (cx0+w, yt), (cx0+w+sk, yt+d),
                     (cx0+sk, yt+d)], closed=True, fc=col, ec="#33424d",
                     lw=0.5, zorder=3+i*0.01))
        ax.add_patch(Polygon([(cx0, yt), (cx0+w, yt), (cx0+w, yt-th),
                     (cx0, yt-th)], closed=True, fc=col, ec="#33424d", lw=0.5,
                     alpha=0.78, zorder=3+i*0.01))
    ax.text(cx0+w+sk+1.2, cyt+d, "z = 0", fontsize=12.8, va="center", zorder=4)
    ax.text(cx0+w+sk+1.2, cyt-5*gap, "−50 m", fontsize=12.8, va="center", zorder=4)
    caption(90, 10.5, "σ-to-z coupling", "cf_export.py · the core", color=CORE)

    # ============ Scene 4: OpenDrift transport ============
    cxL, cyL = 116.5, 34
    lake = Polygon([(107,33),(110,39),(116,41),(123,39),(126,34),(124,28),
                    (118,25),(111,27),(108,30)], closed=True, fc="none",
                   ec="#2f6f9f", lw=1.4, zorder=1.4)
    ax.add_patch(lake)
    vgrad(106, 127, 24, 42, "#bfe0f3", "#2f7fb8", lake, z=1.3)
    # release star + trajectories + particles
    rx, ry = 114, 33
    rng_pts = [(rx+dx, ry+dy) for dx, dy in
               [(4,2),(7,3),(9,1.5),(6,-1),(8,-2),(3,4),(10,4),(5,5),
                (2,-2),(11,2.5),(7,5.5),(9,-2.5)]]
    for (px, py), c in zip(rng_pts, PARTS*3):
        ax.plot([rx, (rx+px)/2, px], [ry, ry+1.2, py], color=c, lw=0.7,
                alpha=0.5, zorder=2)
        ax.add_patch(Circle((px, py), 0.5, fc=c, ec="white", lw=0.4, zorder=3))
    ax.plot(rx, ry, "*", color="#ffd21e", ms=15, mec="black", mew=0.8, zorder=4)
    ax.text(116.5, 22.5, "plastics · oil · HAB · larvae", ha="center",
            fontsize=13.5, style="italic", color="#444", zorder=4)
    caption(116.5, 10.5, "OpenDrift transport", "CF-NetCDF read unchanged")

    # ----- flowing connectors between scenes -----
    import matplotlib.patheffects as pe
    ARR = "#23456b"                              # dark slate, clearly visible
    def flow(x0, x1, y, lab):
        # inset endpoints so the arrow sits inside the gap, not over the boxes
        a = FancyArrowPatch((x0 + 0.35, y), (x1 - 0.35, y), arrowstyle="-|>",
                            mutation_scale=17, lw=3.0, color=ARR, alpha=1.0,
                            zorder=8, capstyle="round")
        a.set_path_effects([pe.withStroke(linewidth=5.6, foreground="white")])
        ax.add_patch(a)
        t = ax.text((x0+x1)/2, y+2.7, lab, ha="center", fontsize=13.5,
                    style="italic", color=ARR, zorder=8)
        t.set_path_effects([pe.withStroke(linewidth=2.4, foreground="white")])
    flow(33, 35.5, 32, "force")
    flow(76.5, 79.5, 32, "run")
    flow(99, 101.5, 32, "export")

    ax.set_ylim(8.5, 57.2)                    # crop empty top/bottom margins (tight title)
    fig.savefig(DOCS / "figure_architecture.png", dpi=300, bbox_inches="tight",
                pad_inches=0.04, facecolor="white")
    plt.close(fig)
    print("wrote figure_architecture.png")


# --------------------------------------------------------------------------- #
def fig_sigma_schematic():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    x = np.linspace(0, 10, 200)
    # bed profile (a basin), water surface at z=0 with slight tilt
    bed = -6 + 4.5 * np.exp(-((x - 5) ** 2) / 8.0) * -1 + 4.5  # smooth basin
    bed = -(6.0 - 3.5 * np.exp(-((x - 5) ** 2) / 6.0))
    surf = 0.15 * np.cos(x / 3)         # mild water-level variation zeta

    # ---- left: terrain-following sigma layers ----
    ax = axes[0]
    sig = np.linspace(0, -1, 8)          # 0 surface -> -1 bed
    ax.fill_between(x, bed, -8, color="#cdb892", zorder=0)   # ground
    for s in sig:
        z = surf + s * (surf - bed)      # z_k = zeta + sigma*(zeta+d), d=-bed
        ax.plot(x, z, color=BLUE, lw=1.2)
    ax.plot(x, surf, color="navy", lw=2)
    ax.plot(x, bed, color="#5b4a2f", lw=2)
    ax.text(5, 0.9, "water surface  ζ", ha="center", color="navy", fontsize=13.5)
    ax.text(5, bed.min() - 0.7, "lake bed  d", ha="center", color="#5b4a2f", fontsize=13.5)
    ax.text(0.3, -3.2, "σ-layers follow\nthe terrain", color=BLUE, fontsize=12.5,
            fontweight="bold")
    ax.set_title("(a) Delft3D-FLOW: terrain-following σ-layers", fontsize=16.5)
    ax.set_ylim(-8, 2); ax.set_xlim(0, 10); ax.axis("off")

    # ---- right: fixed z-levels ----
    ax = axes[1]
    zlev = np.array([0, -1, -2, -3, -5, -7.5])
    ax.fill_between(x, bed, -8, color="#cdb892", zorder=0)
    for z in zlev:
        inside = z > bed
        ax.plot(x, np.full_like(x, z), color=GREEN, lw=1.2)
        # mask portion below bed (dashed grey)
        if np.any(~inside):
            ax.plot(x[~inside], np.full_like(x[~inside], z), color="grey",
                    lw=1.2, ls=":")
    ax.plot(x, surf, color="navy", lw=2)
    ax.plot(x, bed, color="#5b4a2f", lw=2)
    # interpolation arrows from a sample column
    xc = 5.0
    bedc = np.interp(xc, x, bed); surfc = np.interp(xc, x, surf)
    for z in zlev:
        if z > bedc:
            ax.add_patch(FancyArrowPatch((xc - 0.0, z), (xc, z), arrowstyle="-|>",
                         mutation_scale=8, color=ORANGE))
            ax.plot(xc, z, "o", color=ORANGE, ms=4)
    ax.text(0.3, -3.2, "fixed z-levels\n(metres)", color=GREEN, fontsize=12.5,
            fontweight="bold")
    ax.text(6.2, -6.7, "below bed:\nmasked", color="grey", fontsize=13)
    ax.text(5.1, 0.7, "surface clamp\nat z = 0", color=ORANGE, fontsize=13)
    ax.set_title("(b) OpenDrift target: fixed z-levels", fontsize=16.5)
    ax.set_ylim(-8, 2); ax.set_xlim(0, 10); ax.axis("off")

    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.suptitle(r"$z_k=\zeta+\sigma_k\,(\zeta+d)$  : reconstruct each σ-centre depth, "
                 "then interpolate to fixed z-levels", fontsize=16.5, y=0.975)
    fig.savefig(DOCS / "figure_sigma_schematic.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("wrote figure_sigma_schematic.png")


# --------------------------------------------------------------------------- #
def fig_lake_map():
    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        proj = ccrs.Robinson()
        fig = plt.figure(figsize=(11, 5.6))
        ax = plt.axes(projection=proj)
        ax.set_global()
        ax.add_feature(cfeature.LAND, facecolor="#ece6da")
        ax.add_feature(cfeature.OCEAN, facecolor="#dce9f2")
        ax.add_feature(cfeature.COASTLINE, lw=0.4, edgecolor="#888")
        ax.add_feature(cfeature.BORDERS, lw=0.2, edgecolor="#bbb")
        tf = ccrs.PlateCarree()
    except Exception as e:
        print("cartopy unavailable, simple map:", e)
        fig, ax = plt.subplots(figsize=(11, 5.6))
        ax.set_xlim(-180, 180); ax.set_ylim(-60, 80)
        ax.set_facecolor("#dce9f2")
        tf = None
    # label offsets (deg lon, lat) to declutter the European cluster
    off = {"lagdo": (4, -4), "bornos": (-30, -10), "mead": (-3, 6),
           "polyfytos": (10, -12), "trasimeno": (14, -6), "balaton": (16, 2),
           "rotsee": (-34, 6), "erken": (6, 8), "poyang": (6, 6),
           "sea_of_galilee": (8, -10), "eucumbene": (6, -8),
           "nova_ponte": (-30, -6)}
    dmax = max(d["drift"] for d in LAKES.values())
    for k, d in LAKES.items():
        col = GREEN if d["type"] == "natural" else ORANGE
        sz = 60 + 340 * d["drift"] / dmax
        kw = dict(transform=tf) if tf is not None else {}
        ax.scatter(d["lon"], d["lat"], s=sz, c=col, edgecolor="black",
                   lw=0.8, zorder=5, **kw)
        dx, dy = off[k]
        ax.annotate(d["name"], xy=(d["lon"], d["lat"]),
                    xytext=(d["lon"] + dx, d["lat"] + dy), fontsize=14,
                    fontweight="bold", zorder=6,
                    arrowprops=dict(arrowstyle="-", lw=0.5, color="#555"),
                    **(dict(transform=tf) if tf else {}))
    leg = [Line2D([0], [0], marker="o", color="w", markerfacecolor=GREEN,
                  markeredgecolor="k", markersize=10, label="natural lake"),
           Line2D([0], [0], marker="o", color="w", markerfacecolor=ORANGE,
                  markeredgecolor="k", markersize=10, label="reservoir")]
    ax.legend(handles=leg, loc="lower left", fontsize=14, frameon=True)
    ax.set_title("Geographic distribution of the twelve demonstration lakes\n"
                 "(marker size ∝ 36 h mean drift; 36°S to 60°N, all inhabited continents)",
                 fontsize=18, pad=4)
    fig.savefig(DOCS / "figure_lake_map.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("wrote figure_lake_map.png")


# --------------------------------------------------------------------------- #
def fig_drift_scatter():
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    names = list(LAKES)
    dmean = np.array([LAKES[k]["dmean"] for k in names])
    drift = np.array([LAKES[k]["drift"] for k in names])
    cols = [GREEN if LAKES[k]["type"] == "natural" else ORANGE for k in names]

    ax = axes[0]
    ax.scatter(dmean, drift, c=cols, s=160, edgecolor="black", lw=0.9, zorder=3)
    for k in names:
        ax.annotate(LAKES[k]["name"], (LAKES[k]["dmean"], LAKES[k]["drift"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=13.5)
    ax.set_xlabel("approx. mean depth (m)", fontsize=14)
    ax.set_ylabel("36 h mean drift (m)", fontsize=14)
    ax.tick_params(labelsize=12.5)
    ax.set_title("(a) Transport vs. depth", fontsize=16.5)
    ax.grid(alpha=0.3)

    # (b) drift vs |U|max (uses table values)
    umax = {"lagdo":0.030,"bornos":0.028,"mead":0.049,"polyfytos":1.18,
            "trasimeno":0.012,"balaton":0.005,"rotsee":0.018,"erken":0.010,
            "poyang":0.020,"sea_of_galilee":0.032,"eucumbene":0.052,
            "nova_ponte":0.030}
    ax = axes[1]
    uu = np.array([umax[k] for k in names])
    ax.scatter(uu, drift, c=cols, s=160, edgecolor="black", lw=0.9, zorder=3)
    for k in names:
        ax.annotate(LAKES[k]["name"], (umax[k], LAKES[k]["drift"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=13.5)
    ax.set_xscale("log")
    ax.set_xlabel("max surface current |U|$_{max}$ (m s$^{-1}$)", fontsize=14)
    ax.set_ylabel("36 h mean drift (m)", fontsize=14)
    ax.tick_params(labelsize=12.5, which="both")
    ax.set_title("(b) Transport vs. current strength", fontsize=16.5)
    ax.grid(alpha=0.3, which="both")
    leg = [Line2D([0],[0],marker="o",color="w",markerfacecolor=GREEN,
                  markeredgecolor="k",markersize=12,label="natural"),
           Line2D([0],[0],marker="o",color="w",markerfacecolor=ORANGE,
                  markeredgecolor="k",markersize=12,label="reservoir")]
    ax.legend(handles=leg, fontsize=14, loc="lower right")
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.suptitle("Transport across the twelve lakes; drift reflects basin size, depth, "
                 "fetch and wind exposure —\nnot peak current alone "
                 "(cf. Polyfytos: strong localised river jet, moderate drift)",
                 fontsize=18, y=0.98)
    fig.savefig(DOCS / "figure_drift_scatter.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("wrote figure_drift_scatter.png")


# --------------------------------------------------------------------------- #
def _cell_edges(c):
    """Midpoint cell edges for a 1-D (possibly non-uniform) coordinate."""
    c = np.asarray(c, float)
    m = (c[:-1] + c[1:]) / 2.0
    return np.concatenate([[c[0] - (m[0] - c[0])], m, [c[-1] + (c[-1] - m[-1])]])


def fig_vertical_sigma_z(prefix="erken"):
    """Depth-vs-time forcing at the deepest water column: temperature and
    (log-scale) current speed on the exported z-levels."""
    from matplotlib.colors import LogNorm
    ds = xr.open_dataset(OUT / f"{prefix}_forcing.nc")
    z = ds["depth"].values
    temp = ds["temp"].values                       # (time, depth, lat, lon)
    spd = np.sqrt(ds["u"].values**2 + ds["v"].values**2)
    # pick the column with the most finite z-levels (the deepest wet column)
    finite_depth = np.isfinite(temp[0]).sum(axis=0)
    j, i = np.unravel_index(np.nanargmax(finite_depth), finite_depth.shape)
    T = temp[:, :, j, i]                            # (time, depth)
    S = spd[:, :, j, i]
    valid = np.isfinite(T).any(axis=0)             # drop all-NaN deep levels
    zk = z[valid]
    T = T[:, valid].T                              # (depth, time)
    S = S[:, valid].T
    hours = np.arange(T.shape[1])
    ze = _cell_edges(zk)
    ylo, yhi = ze.min(), ze.max()                  # crop white space below bed

    fig, axs = plt.subplots(1, 2, figsize=(13, 5.4))
    # (a) temperature
    pm = axs[0].pcolormesh(hours, zk, np.ma.masked_invalid(T),
                           cmap="inferno", shading="auto")
    cb = fig.colorbar(pm, ax=axs[0], fraction=0.046, pad=0.02)
    cb.set_label("temperature (°C)", fontsize=14); cb.ax.tick_params(labelsize=12.5)
    axs[0].set_title("(a) temperature on z-levels", fontsize=16.5)
    # (b) current speed on a logarithmic colour scale; clip zeros/tiny values
    # up to the floor so they fill with the lowest colour instead of white
    spos = S[np.isfinite(S) & (S > 0)]
    vmin = max(spos.min(), 1e-4) if spos.size else 1e-4
    Sm = np.ma.masked_invalid(np.clip(S, vmin, None))   # NaN (sub-bed) stays masked
    pm = axs[1].pcolormesh(hours, zk, Sm, cmap="viridis", shading="auto",
                           norm=LogNorm(vmin=vmin, vmax=np.nanmax(S)))
    cb = fig.colorbar(pm, ax=axs[1], fraction=0.046, pad=0.02)
    cb.set_label("current speed (m s$^{-1}$, log scale)", fontsize=14)
    cb.ax.tick_params(labelsize=12.5)
    axs[1].set_title("(b) current speed on z-levels (log scale)", fontsize=16.5)
    for a in axs:
        a.set_xlabel("hours", fontsize=14); a.set_ylim(ylo, yhi)
        a.tick_params(labelsize=12.5)
    axs[0].set_ylabel("depth (m)", fontsize=14)
    # enlarge the panels and leave a small gap between the suptitle and the panel
    # titles (reserve a thin top strip for the suptitle)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.suptitle(f"{LAKES[prefix]['name']}: depth-resolved forcing from the σ-to-z "
                 "coupling (deepest column, 2-day run)", fontsize=18, y=0.97)
    fig.savefig(OUT / "figure_vertical_sigma_z.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("wrote figure_vertical_sigma_z.png")


def fig_forcing_example(prefix="polyfytos"):
    f = OUT / f"{prefix}_forcing.nc"
    ds = xr.open_dataset(f)
    u = np.nanmean(ds["u"].isel(depth=0).values, axis=0)
    v = np.nanmean(ds["v"].isel(depth=0).values, axis=0)
    spd = np.sqrt(u**2 + v**2)
    temp = np.nanmean(ds["temp"].isel(depth=0).values, axis=0)
    hs = np.nanmean(ds["Hs"].values, axis=0) if "Hs" in ds else None
    LON, LAT = np.meshgrid(ds.lon.values, ds.lat.values)

    fig, axs = plt.subplots(1, 3, figsize=(16, 5.0))
    fig.subplots_adjust(top=0.895, bottom=0.04, left=0.02, right=0.98, wspace=0.08)
    for a in axs:
        a.set_facecolor("#e8e8e8"); a.set_xticks([]); a.set_yticks([])
        a.set_aspect("equal")

    from matplotlib.ticker import MaxNLocator
    def cbar_under(pm, a, label, nbins=6):
        cb = fig.colorbar(pm, ax=a, orientation="horizontal",
                          fraction=0.058, pad=0.04, aspect=32)
        cb.set_label(label, fontsize=16.5)
        cb.ax.tick_params(labelsize=13.5)
        cb.locator = MaxNLocator(nbins=nbins); cb.update_ticks()

    # (a) currents: speed + quiver
    pm = axs[0].pcolormesh(ds.lon, ds.lat, np.ma.masked_invalid(spd),
                           cmap="turbo", shading="auto")
    st = max(1, LON.shape[0] // 22)
    axs[0].quiver(LON[::st, ::st], LAT[::st, ::st], u[::st, ::st], v[::st, ::st],
                  scale=8, width=0.004, color="black", alpha=0.6)
    cbar_under(pm, axs[0], "|U| (m s$^{-1}$)")
    axs[0].set_title("(a) Mean surface current", fontsize=18)

    # (b) temperature
    pm = axs[1].pcolormesh(ds.lon, ds.lat, np.ma.masked_invalid(temp),
                           cmap="RdYlBu_r", shading="auto")
    cbar_under(pm, axs[1], "T (°C)", nbins=4)
    axs[1].set_title("(b) Surface temperature", fontsize=18)

    # (c) significant wave height
    if hs is not None:
        pm = axs[2].pcolormesh(ds.lon, ds.lat, np.ma.masked_invalid(hs),
                               cmap="viridis", shading="auto")
        cbar_under(pm, axs[2], "H$_s$ (m)")
        axs[2].set_title("(c) Significant wave height", fontsize=18)
    else:
        axs[2].axis("off")

    fig.suptitle(f"Exported surface forcing fields for "
                 f"{LAKES.get(prefix,{}).get('name',prefix)} "
                 "— a single coupled FLOW+WAVE run, OpenDrift-ready",
                 fontsize=19.5, y=0.94)
    fig.savefig(DOCS / "figure_forcing_example.png", dpi=300, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    print("wrote figure_forcing_example.png")


if __name__ == "__main__":
    fig_architecture()
    fig_sigma_schematic()
    fig_lake_map()
    fig_drift_scatter()
    fig_forcing_example("polyfytos")
