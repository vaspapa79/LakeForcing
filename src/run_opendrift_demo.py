"""
run_opendrift_demo.py -- validate the CF-NetCDF by driving OpenDrift with it.

Confirms (a) the generic reader ingests our file, (b) the z-levels are read as
metres (not sigma indices), (c) particles actually advect. Run in the `plastic`
conda env:

    conda run --no-capture-output -n plastic python src/run_opendrift_demo.py \
        --forcing output/polyfytos_forcing.nc --lon 21.95 --lat 40.20
"""
import argparse
from opendrift.models.oceandrift import OceanDrift
from opendrift.readers import reader_netCDF_CF_generic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcing", required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--radius", type=float, default=300,
                    help="release radius in metres (hard-bounded, uniform)")
    ap.add_argument("--wind-drift-factor", type=float, default=0.02,
                    help="windage coefficient (fraction of 10 m wind); 0 disables")
    ap.add_argument("--out", default="output/demo_trajectory.nc")
    args = ap.parse_args()

    o = OceanDrift(loglevel=20)
    r = reader_netCDF_CF_generic.Reader(args.forcing)
    print(r)                                   # prints variables + z-levels found
    o.add_reader(r)

    # INLAND LAKE: OpenDrift's global coastline treats the lake as land and would
    # strand every particle at step 0. Disable the auto-landmask so stranding is
    # governed by the reader's own data coverage (NaN outside the lake).
    o.set_config("general:use_auto_landmask", False)
    o.set_config("environment:fallback:land_binary_mask", 0)  # all water (lake)

    # surface release of buoyant tracer (z=0). Transport = current + Stokes +
    # windage (wind_drift_factor * 10 m wind), matching the motivating physics;
    # windage applies only when the forcing carries x_wind/y_wind.
    o.set_config("drift:vertical_mixing", False)
    o.set_config("drift:stokes_drift", True)
    # radius_type="uniform" hard-bounds particles within `radius` (the default
    # "gaussian" uses radius as a std-dev, scattering ~2.5x wider -> particles
    # land outside small lakes).
    o.seed_elements(lon=args.lon, lat=args.lat, z=0,
                    radius=args.radius, radius_type="uniform", number=args.n,
                    time=r.start_time, wind_drift_factor=args.wind_drift_factor)

    o.run(duration=__import__("datetime").timedelta(hours=args.hours),
          time_step=600, outfile=args.out)
    print(o)
    print("start", r.start_time, "-> end", r.end_time)


if __name__ == "__main__":
    main()
