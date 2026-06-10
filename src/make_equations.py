"""
make_equations.py -- render the manuscript display equations as tight, high-DPI
PNGs (matplotlib mathtext) for embedding in the .docx. One file per marker name
used in paper/EMS_manuscript.md ([[EQ:name]]).

  python src/make_equations.py   ->  docs/eq/EQ_<name>.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

EQDIR = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift/docs/eq")
EQDIR.mkdir(parents=True, exist_ok=True)

# name -> mathtext (matplotlib subset: \mathrm for text, no \text/\dfrac/\big)
EQ = {
    "windspeed": r"$U_{10}=\sqrt{u_{10}^{\,2}+v_{10}^{\,2}}$",
    "winddir":   r"$\theta_{w}=\left[\frac{180}{\pi}\,\mathrm{atan2}(-u_{10},\,-v_{10})\right]\ \mathrm{mod}\ 360^{\circ}$",
    "magnus":    r"$\mathrm{RH}=100\,\exp\!\left[\frac{a\,T_{d}}{b+T_{d}}-\frac{a\,T_{a}}{b+T_{a}}\right],\qquad a=17.625,\ \ b=243.04$",
    "sigmaz":    r"$z_{k}=\zeta+\sigma_{k}\,(\zeta+d),\qquad \sigma_{k}\in[\,0,\,-1\,]$",
    "rotation":  r"$u_{E}=u_{\xi}\cos\alpha-v_{\eta}\sin\alpha,\qquad v_{N}=u_{\xi}\sin\alpha+v_{\eta}\cos\alpha$",
    "stokes":    r"$\omega=\frac{2\pi}{T_{p}},\qquad k=\frac{\omega^{2}}{g},\qquad a=\frac{H_{s}}{2\sqrt{2}},\qquad |U_{s}|=\omega\,k\,a^{2}$",
    "radius":    r"$r=\min\!\left(r_{\max},\,0.6\,D_{\mathrm{shore}}\right),\qquad D_{\mathrm{shore}}=\max\,\mathrm{EDT}(\mathrm{wet\ mask})$",
    "drift":     r"$D_{i}=\sqrt{\left[(\lambda_{i}-\lambda_{0})\cos\phi\,R_{e}\right]^{2}+\left[(\phi_{i}-\phi_{0})\,R_{e}\right]^{2}}\,,\qquad R_{e}\approx111\ \mathrm{km\ deg^{-1}}$",
}


def render(name, tex, fontsize=22, dpi=200):
    fig = plt.figure(figsize=(0.1, 0.1))
    t = fig.text(0.0, 0.0, tex, fontsize=fontsize)
    out = EQDIR / f"EQ_{name}.png"
    fig.savefig(out, dpi=dpi, bbox_inches="tight", pad_inches=0.06,
                facecolor="white")
    plt.close(fig)
    return out


if __name__ == "__main__":
    for nm, tex in EQ.items():
        p = render(nm, tex)
        print("wrote", p.name)
