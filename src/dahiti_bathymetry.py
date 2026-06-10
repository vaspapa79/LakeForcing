"""
dahiti_bathymetry.py -- list and download lake bathymetry from DAHITI (TU Munich)
using the existing API key. Bathymetry is GeoTIFF at ~0.0001 deg (~10 m).

DAHITI API v2: https://dahiti.dgfi.tum.de/api/v2/
  list-targets/        POST {api_key}            -> all targets
  get-target-info/     POST {api_key, dahiti_id} -> per-target product availability
  download-bathymetry/ POST {api_key, dahiti_id} -> bathymetry (GeoTIFF)

Usage:
  python src/dahiti_bathymetry.py --list                 # enumerate bathymetry targets
  python src/dahiti_bathymetry.py --download 13340 13676  # by dahiti_id
"""
import argparse, json, ssl, urllib.request, base64
from pathlib import Path

CREDS = Path(r"C:/Users/vaspapa/Desktop/Greek_lakes/dahiti_credentials.json")
BASE = "https://dahiti.dgfi.tum.de/api/v2/"
OUT = Path(r"C:/Users/vaspapa/Desktop/LakeForcing_OpenDrift/bathymetry/dahiti")
CTX = ssl.create_default_context()


def key():
    return json.load(open(CREDS))["api_key"]


def post(ep, payload, raw=False):
    data = json.dumps({**payload, "api_key": key()}).encode()
    req = urllib.request.Request(BASE + ep, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
        body = r.read()
    return body if raw else json.loads(body.decode())


def list_targets():
    res = post("list-targets/", {})
    if isinstance(res, dict):
        res = res.get("data") or res.get("targets") or list(res.values())[0]
    return res


def has_bathymetry(target):
    """list-targets returns data_access.bathymetry = 'public'/None per target."""
    da = target.get("data_access") or {}
    return da.get("bathymetry") not in (None, "", "none")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--probe", type=int, help="dump get-target-info for one id")
    ap.add_argument("--download", nargs="+", type=int)
    args = ap.parse_args()

    if args.probe:
        print(json.dumps(post("get-target-info/", {"dahiti_id": args.probe}), indent=2)[:2000])
        return

    if args.list:
        tg = list_targets()
        hits = [t for t in tg if has_bathymetry(t)]
        print(f"{len(tg)} total DAHITI targets; {len(hits)} with public bathymetry\n")
        print(f"{'id':>7}  {'name':34s} {'country':14s} {'lon':>8} {'lat':>8}")
        print("-" * 78)
        for t in sorted(hits, key=lambda x: (x.get("continent",""), x.get("target_name",""))):
            tid = t.get("dahiti_id")
            nm = (t.get("target_name") or "")[:34]
            co = (t.get("country") or "")[:14]
            print(f"{tid:7d}  {nm:34s} {co:14s} {t.get('longitude',0):8.2f} {t.get('latitude',0):8.2f}")
        print("-" * 78)
        ids = [t.get("dahiti_id") for t in hits]
        Path(OUT).mkdir(parents=True, exist_ok=True)
        (OUT / "bathymetry_targets.json").write_text(json.dumps(hits, indent=2))
        print(f"ids: {ids}")
        print(f"saved -> {OUT / 'bathymetry_targets.json'}")
        return

    if args.download:
        OUT.mkdir(parents=True, exist_ok=True)
        for tid in args.download:
            try:
                body = post("download-bathymetry/", {"dahiti_id": tid, "format": "geotiff"}, raw=True)
                # API may return JSON {data: base64} or raw bytes
                if body[:1] in (b"{", b"["):
                    j = json.loads(body.decode())
                    raw = base64.b64decode(j["data"]) if "data" in j else None
                    if raw is None:
                        print(tid, "-> JSON without data:", str(j)[:200]); continue
                    body = raw
                f = OUT / f"dahiti_{tid}_bathymetry.tif"
                f.write_bytes(body)
                print(f"wrote {f}  ({len(body)/1e3:.0f} kB)")
            except Exception as e:
                print(tid, "FAILED:", str(e)[:160])


if __name__ == "__main__":
    main()
