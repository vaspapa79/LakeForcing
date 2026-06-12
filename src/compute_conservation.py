"""
compute_conservation.py -- quantify how much the linear sigma-to-z reconstruction
changes the depth-integrated horizontal transport (a bound on the non-conservation
of the export, for Section 2.5).

For a representative full-length lake we compare, per wet column and output time:
  - the native depth-averaged velocity, a thickness-weighted average over the
    Delft3D sigma layers (which integrate exactly over the water column), and
  - the depth-averaged velocity obtained by integrating the fixed z-level
    reconstruction (cf_export.sigma_to_z) over the same column.
Reports the median and mean relative difference of the transport magnitude.

  conda run -n plastic python src/compute_conservation.py
"""
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cf_export import read_trim, sigma_to_z, Z_LEVELS   # noqa: E402

ROOT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift")
# Bornos: moderate currents and a maximum depth (~20 m) well within the z-level set,
# so the metric isolates the interpolation error (no deep-truncation artefact). The
# source CRS is irrelevant here -- only u, v, s1, dps, sig are used.
LAKE = "bornos"
TRIM = ROOT / "models" / LAKE / f"trim-{LAKE}.nc"
CRS = "EPSG:32630"


def sigma_edges(sig):
    """Layer-centre fractions (0..-1) -> layer edges (0 at surface, -1 at bed)."""
    sig = np.asarray(sig)
    edges = np.empty(sig.size + 1)
    edges[0] = 0.0
    edges[-1] = -1.0
    edges[1:-1] = 0.5 * (sig[:-1] + sig[1:])
    return edges


def main():
    f = read_trim(TRIM, CRS)
    # subsample time (6 representative hours) -- the metric is a per-column average,
    # so a handful of snapshots gives a stable estimate without the full 49 steps
    tsel = np.linspace(12, f["u"].shape[0] - 1, 6).astype(int)
    u, v = f["u"][tsel], f["v"][tsel]     # (time,K,N,M) east/north, cell centres
    s1, dps, sig = f["s1"][tsel], f["dps"], f["sig"]
    nt, nk, nn, nm = u.shape
    edges = sigma_edges(sig)
    thick = np.abs(np.diff(edges))        # (K,) sigma-layer thickness fractions

    # native depth-averaged velocity: thickness-weighted mean over sigma layers
    w = thick[None, :, None, None]
    ubar_n = np.nansum(u * w, axis=1)     # (time,N,M)
    vbar_n = np.nansum(v * w, axis=1)

    # z-level reconstruction of the same fields, then depth-average over the column
    uz = sigma_to_z(u, s1, dps, sig)      # (time,nz,N,M)
    vz = sigma_to_z(v, s1, dps, sig)
    Z = np.asarray(Z_LEVELS)
    H = s1 + dps                          # (time,N,M) total depth

    def col_average(fz):
        # trapezoidal integral of fz over depth 0..-H using valid (above-bed) levels,
        # divided by H; piecewise-constant tail from deepest valid level to the bed.
        out = np.full((nt, nn, nm), np.nan)
        for t in range(nt):
            d = np.maximum(H[t], 1e-6)
            for n in range(nn):
                for m in range(nm):
                    col = fz[t, :, n, m]
                    val = np.isfinite(col)
                    if val.sum() < 1 or not np.isfinite(d[n, m]):
                        continue
                    zz = Z[val]; ff = col[val]
                    dd = d[n, m]
                    # integrate from 0 down to -dd
                    acc = 0.0
                    for i in range(len(zz) - 1):
                        dz = zz[i] - zz[i + 1]
                        acc += 0.5 * (ff[i] + ff[i + 1]) * dz
                    # tail from last valid level to bed (constant)
                    tail = (-zz[-1]) if (-zz[-1]) < dd else dd
                    acc += ff[-1] * max(dd + zz[-1], 0.0)
                    out[t, n, m] = acc / dd
        return out

    ubar_z = col_average(uz)
    vbar_z = col_average(vz)

    sp_n = np.hypot(ubar_n, vbar_n)
    err = np.hypot(ubar_z - ubar_n, vbar_z - vbar_n)
    Hmean = np.nanmean(s1 + dps, axis=0)                          # (N,M)
    deep_ok = Hmean < 0.95 * (-Z[-1])                             # within z-range
    wet = (np.isfinite(sp_n) & np.isfinite(err) & (sp_n > 0.005)
           & deep_ok[None])                                       # >0.5 cm/s, no truncation
    rel = err[wet] / sp_n[wet]
    res = dict(lake=LAKE, n_samples=int(wet.sum()),
               median_rel_transport_error=round(float(np.median(rel)), 4),
               mean_rel_transport_error=round(float(np.mean(rel)), 4),
               p90_rel_transport_error=round(float(np.percentile(rel, 90)), 4))
    (ROOT / "output" / "conservation.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
