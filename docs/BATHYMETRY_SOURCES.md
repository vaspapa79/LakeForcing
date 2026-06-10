# Lake bathymetry sources for enrichment

Status of open lake-bathymetry sources evaluated 2026-06-08, to extend the
`Lake Data.zip` corpus (19 European/Greek lakes) toward a global spread.

## ✅ DAHITI — primary global route (credentials already held)
- **What:** 71 lakes/reservoirs with public bathymetry, GeoTIFF, ~0.0001° (~10 m),
  EPSG:4326. Values = **bed elevation in metres** (convert to depth vs surface level).
- **Access:** API v2 `https://dahiti.dgfi.tum.de/api/v2/`, key in
  `Greek_lakes/dahiti_credentials.json`. Endpoints: `list-targets/`
  (each target has `data_access.bathymetry = "public"/null`),
  `download-bathymetry/` `{api_key, dahiti_id}`.
- **Tooling:** `src/dahiti_bathymetry.py --list` (enumerate, saved to
  `bathymetry/dahiti/bathymetry_targets.json`) and `--download <ids...>`.
- **Validated:** downloaded Sea of Galilee (13705) + Forggensee (10341) OK.
- **Global value:** Africa (Naivasha, Nakuru, Elementaita, Solai, Lagdo, Bankim,
  Massingir, Gilgel Gibe III), Middle East (Dead Sea, Sea of Galilee, Mosul,
  Tharthar), Asia (Poyang, Siling Co, Dagze Co, Lena R.), Australia (Eucumbene),
  Americas (Mead, Salton Sea, Fort Peck, Texoma + many US/Brazil reservoirs,
  Enriquillo, Tunas Grandes), Europe (Orellana, Yesa, Zujar, Forggensee).
  → exactly the latitudes/climates the European corpus lacks.

## ✅ GLOBathy — full global coverage (modelled)
- **What:** bathymetry for 1.4M+ lakes (HydroLAKES-aligned), Dmax + h-A-V.
  Modelled (GIS framework from max-depth + geometry), not surveyed.
- **Access:** figshare collection
  `https://springernature.figshare.com/collections/.../5243309`; also mirrored in
  the Google Earth Engine community catalog (`projects/sat-io/open-datasets/GLOBathy`).
- **Use:** fallback for any lake without a survey; good for big lakes if not in DAHITI.

## ⚠️ GEBCO 2024 grid — ONLY the truly large/deep lakes, no auth
- **What:** global 15-arcsec grid (elevation m, a.s.l.).
- **Access (no download of the 7 GB grid):** windowed `/vsicurl/` read of the COG
  `https://data.source.coop/alexgleith/gebco-2024/GEBCO_2024.tif` via
  `src/gebco_subset.py --name <x> --bbox W S E N`.
- **CRITICAL CAVEAT (verified 2026-06-08):** GEBCO only has REAL bathymetry for big
  lakes with incorporated soundings. Mid/shallow lakes are **flat-filled at surface
  level**. Confirmed by interior-pixel std:
    - Baikal ✅ std 558 (bed to −1198 m) · Superior ✅ std 37 → KEPT
    - Geneva ❌ flat 355 m · Victoria ❌ std 0 (flat 1134 m) → REJECTED
  ALWAYS verify interior std before trusting a GEBCO lake. For rejected lakes use
  DAHITI, national surveys, or White-Nile HRBS (Victoria).

## ✅ Great Lakes of the White Nile (Victoria, Albert, Edward, George)
- **What:** HRBS-GLWNB 2020, high-res surveyed bathymetry+shoreline from ~18M
  acoustic soundings. Nature Sci Data `s41597-022-01742-3`.

## ✅ NOAA NCEI Great Lakes bathymetry
- **What:** surveyed grids for Superior/Michigan/Huron/Erie/Ontario.
- **Access:** `https://www.ncei.noaa.gov/products/great-lakes-bathymetry` (Grid Extract).

## ❌ Bathybase — DEAD (do not use)
- `bathybase.org` was a 1,322-lake open repo but the **domain is now squatted**
  (serves an online-betting site "Baji Bangladesh"; lake records 404). Excluded.

---
### Recommended enrichment plan
1. **DAHITI** for the global spread (script ready; pick ~10–15 across continents).
2. **GEBCO** for a few iconic large lakes (Great Lakes, Geneva, Baikal, Titicaca).
3. **GLOBathy** as the catch-all fallback for anything missing.
Keep the surveyed `Lake Data.zip` corpus as the high-quality European core.
