"""
validate_polyfytos.py -- benchmark the AUTO-generated closed-lake configuration
against the hand-built, peer-reviewed Polyfytos model (Papaioannou et al., 2025)
on the shared grid. Reports RMSE + vector correlation of surface currents, RMSE of
surface temperature, and bias in significant wave height, and draws Figure 8
(hand-built vs auto surface fields + scatter).

  conda run -n plastic python src/validate_polyfytos.py
"""
import json
from pathlib import Path
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cf_export import read_trim

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
HAND = ROOT / "models/polyfytos/trim-polifitos.nc"
AUTO = ROOT / "models/polyfytos_auto/trim-polyfytos_auto.nc"
HW = ROOT / "models/polyfytos/wavm-polifitos.nc"
AW = ROOT / "models/polyfytos_auto/wavm-polyfytos_auto.nc"
CRS = "EPSG:32634"


def surf_mean(trim):
    f = read_trim(trim, CRS)
    u = np.nanmean(f["u"][:, 0], axis=0)   # time-mean surface (layer 0), east
    v = np.nanmean(f["v"][:, 0], axis=0)   # north
    t = (np.nanmean(f["temp"][:, 0], axis=0) if f["temp"] is not None else None)
    return f["lon"], f["lat"], u, v, t


def hs_mean(wavm):
    if not Path(wavm).exists():
        return None
    w = xr.open_dataset(wavm)
    for nm in ("hsign", "HSIGN"):
        if nm in w.variables:
            a = np.asarray(w[nm].values, float)
            w.close()
            return np.nanmean(a, axis=0) if a.ndim == 3 else a
    w.close()
    return None


def main():
    lon, lat, uh, vh, th = surf_mean(HAND)
    _, _, ua, va, ta = surf_mean(AUTO)
    sh, sa = np.hypot(uh, vh), np.hypot(ua, va)
    wet = np.isfinite(sh) & np.isfinite(sa) & (sh >= 0) & (sa >= 0)

    # speed RMSE
    rmse_spd = float(np.sqrt(np.nanmean((sa[wet] - sh[wet]) ** 2)))
    bias_spd = float(np.nanmean(sa[wet] - sh[wet]))
    # complex (vector) correlation of the velocity field
    zh = (uh + 1j * vh)[wet]
    za = (ua + 1j * va)[wet]
    cc = np.vdot(zh - zh.mean(), za - za.mean()) / (
        np.linalg.norm(zh - zh.mean()) * np.linalg.norm(za - za.mean()))
    vec_corr_mag = float(abs(cc))
    vec_corr_ang = float(np.degrees(np.angle(cc)))
    # speed Pearson r
    r_spd = float(np.corrcoef(sh[wet], sa[wet])[0, 1])
    # temperature RMSE
    rmse_t = None
    if th is not None and ta is not None:
        wt = wet & np.isfinite(th) & np.isfinite(ta)
        rmse_t = float(np.sqrt(np.nanmean((ta[wt] - th[wt]) ** 2)))
        bias_t = float(np.nanmean(ta[wt] - th[wt]))
    # Hs bias
    hh, ha = hs_mean(HW), hs_mean(AW)
    bias_hs = None
    if hh is not None and ha is not None and hh.shape == ha.shape:
        m = np.isfinite(hh) & np.isfinite(ha) & (hh > 0) & (ha > 0)
        bias_hs = float(np.nanmean(ha[m] - hh[m]))
        rmse_hs = float(np.sqrt(np.nanmean((ha[m] - hh[m]) ** 2)))

    res = dict(rmse_speed_ms=rmse_spd, bias_speed_ms=bias_spd, r_speed=r_spd,
               vec_corr_mag=vec_corr_mag, vec_corr_ang_deg=vec_corr_ang,
               rmse_temp_C=rmse_t, bias_temp_C=bias_t if th is not None else None,
               bias_hs_m=bias_hs, n_cells=int(wet.sum()))
    (ROOT / "output" / "polyfytos_validation.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))

    # ---------- Figure 8 ----------
    fig, ax = plt.subplots(2, 3, figsize=(13.5, 8))
    def panel(a, fld, title, cmap, vmax=None):
        m = np.ma.masked_invalid(np.where(wet, fld, np.nan))
        pm = a.pcolormesh(m, cmap=cmap, shading="auto", vmin=0, vmax=vmax)
        a.set_xticks([]); a.set_yticks([]); a.set_aspect("equal")
        a.set_title(title, fontsize=18)
        fig.colorbar(pm, ax=a, fraction=0.046, pad=0.02)
    smax = float(np.nanpercentile(np.r_[sh[wet], sa[wet]], 98))
    panel(ax[0, 0], sh, "(a) Hand-built surface speed (m s$^{-1}$)", "turbo", smax)
    panel(ax[0, 1], sa, "(b) Auto-generated surface speed (m s$^{-1}$)", "turbo", smax)
    # scatter
    ax[0, 2].plot(sh[wet], sa[wet], ".", ms=1.5, alpha=0.3, color="#2c6fbb")
    lim = max(sh[wet].max(), sa[wet].max())
    ax[0, 2].plot([0, lim], [0, lim], "k--", lw=1)
    ax[0, 2].set_xlabel("hand-built |U| (m s$^{-1}$)", fontsize=16.5)
    ax[0, 2].set_ylabel("auto |U| (m s$^{-1}$)", fontsize=16.5)
    ax[0, 2].set_title(f"(c) Surface speed: r={r_spd:.2f}, "
                       f"RMSE={rmse_spd*100:.1f} cm s$^{{-1}}$", fontsize=18)
    ax[0, 2].set_aspect("equal")
    if th is not None and ta is not None:
        tmin = float(np.nanmin(np.r_[th[wt], ta[wt]])); tmax = float(np.nanmax(np.r_[th[wt], ta[wt]]))
        for a, fld, lab in [(ax[1, 0], th, "(d) Hand-built T (°C)"),
                            (ax[1, 1], ta, "(e) Auto-generated T (°C)")]:
            mm = np.ma.masked_invalid(np.where(wt, fld, np.nan))
            pm = a.pcolormesh(mm, cmap="RdYlBu_r", shading="auto", vmin=tmin, vmax=tmax)
            a.set_xticks([]); a.set_yticks([]); a.set_aspect("equal"); a.set_title(lab, fontsize=18)
            fig.colorbar(pm, ax=a, fraction=0.046, pad=0.02)
        ax[1, 2].plot(th[wt], ta[wt], ".", ms=1.5, alpha=0.3, color="#c0392b")
        lo, hi = tmin, tmax
        ax[1, 2].plot([lo, hi], [lo, hi], "k--", lw=1)
        ax[1, 2].set_xlabel("hand-built T (°C)", fontsize=16.5)
        ax[1, 2].set_ylabel("auto T (°C)", fontsize=16.5)
        ax[1, 2].set_title(f"(f) Surface T: RMSE={rmse_t:.2f} °C", fontsize=18)
        ax[1, 2].set_aspect("equal")
    fig.suptitle("Auto-generated closed-lake configuration vs hand-built Polyfytos model "
                 "(shared grid, 48 h mean surface fields)", fontsize=19.5, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = ROOT / "docs" / "figure_validation.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    print("wrote", out)


if __name__ == "__main__":
    main()
