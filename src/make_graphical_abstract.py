"""
make_graphical_abstract.py -- Elsevier graphical abstract for LakeForcing-OpenDrift,
plate-assembled from the paper's OWN rendered figures (not cartoons, not AI):
open global data -> coupled Delft3D-FLOW/WAVE -> sigma-to-z CF-NetCDF -> OpenDrift.
Each stage is a real, tightly-cropped paper plot, placed WITHOUT distortion (aspect
preserved, centred) inside a titled rounded box; arrows link the stages; a results
banner sits below. >=300 dpi.

  python src/make_graphical_abstract.py
"""
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
DOCS, OUT = ROOT / "docs", ROOT / "output"
PAN, CORE, ARR = "#ffffff", "#c0392b", "#23456b"
PANE = "#c4d2e2"
FIGW, FIGH = 10.0, 4.7

# (figure, tight fractional crop l,t,r,b, short title, edge colour). Crops are
# tight to a SINGLE clean panel so no neighbouring panel bleeds in.
STAGES = [
    (DOCS / "figure_lake_map.png",        None,
     "Open global data\nbathymetry + ERA5", PANE),
    (DOCS / "figure_forcing_example.png", (0.035, 0.115, 0.320, 0.955),
     "Coupled Delft3D\nFLOW + WAVE (SWAN)", PANE),
    (OUT / "figure_vertical_sigma_z.png", (0.035, 0.090, 0.455, 0.975),
     "σ-to-z CF-NetCDF\nexport", CORE),
    (OUT / "figure_demonstration.png",    (0.010, 0.350, 0.250, 0.640),
     "OpenDrift\nparticle transport", PANE),
]


def load_crop(path, box):
    im = Image.open(path).convert("RGB")
    if box:
        W, H = im.size
        l, t, r, b = box
        im = im.crop((int(l * W), int(t * H), int(r * W), int(b * H)))
    return np.asarray(im)


def main():
    fig = plt.figure(figsize=(FIGW, FIGH))
    bg = fig.add_axes([0, 0, 1, 1]); bg.set_xlim(0, 1); bg.set_ylim(0, 1); bg.axis("off")

    bg.text(0.5, 0.955, "LakeForcing-OpenDrift: from open data to lake transport "
            "forcing", ha="center", va="center", fontsize=14.5, fontweight="bold",
            color="#15233a")

    L, gap = 0.018, 0.045
    bw = (1 - 2 * L - 3 * gap) / 4
    yb, yt = 0.300, 0.855
    h = yt - yb
    ymid = (yb + yt) / 2

    def place(img, area):
        """Put img in `area` (x,y,w,h fig-fraction), preserving aspect, centred."""
        hp, wp = img.shape[:2]
        A = wp / hp
        aw, ah = area[2] * FIGW, area[3] * FIGH        # inches available
        if A > aw / ah:                                # width-limited
            dw, dh = aw, aw / A
        else:                                          # height-limited
            dh, dw = ah, ah * A
        fw, fh = dw / FIGW, dh / FIGH
        fx = area[0] + (area[2] - fw) / 2
        fy = area[1] + (area[3] - fh) / 2
        ax = fig.add_axes([fx, fy, fw, fh], zorder=3)
        ax.imshow(img); ax.axis("off")

    for i, (path, box, title, ec) in enumerate(STAGES):
        x0 = L + i * (bw + gap)
        bg.add_patch(FancyBboxPatch((x0 + 0.004, yb - 0.008), bw, h,
                     boxstyle="round,pad=0.004,rounding_size=0.018", fc="#000000",
                     ec="none", alpha=0.08, zorder=1))
        bg.add_patch(FancyBboxPatch((x0, yb), bw, h,
                     boxstyle="round,pad=0.004,rounding_size=0.018", fc=PAN, ec=ec,
                     lw=2.4 if ec == CORE else 1.4, zorder=2))
        bg.text(x0 + bw / 2, yt - 0.030, title, ha="center", va="top", fontsize=8.7,
                fontweight="bold", color=CORE if ec == CORE else "#1a1a1a", zorder=4)
        place(load_crop(path, box),
              (x0 + 0.012, yb + 0.030, bw - 0.024, (yt - 0.120) - (yb + 0.030)))

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
