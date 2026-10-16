#!/usr/bin/env python3
"""Statistics of ESP cube files, to choose a colour range.

For each folder (or ESP.cube file) it prints min, max, mean, standard deviation
and percentiles of the whole grid. If Dt.cube lies next to it, it also prints
the ESP values on the density isosurface (--iso). Those are the values the
surface is actually coloured with, so they are the better basis for a colour
scale. With several molecules it ends with one common range for all of them.

Examples:
    python describe_esp.py results/water
    python describe_esp.py results/*/ --iso 0.002
"""
import argparse
import os

import numpy as np

from cube_tools import read_cube, surface_values


def esp_path(p):
    return os.path.join(p, "ESP.cube") if os.path.isdir(p) else p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="result folders or ESP.cube files")
    ap.add_argument("--iso", type=float, default=0.002, help="density isovalue in e/bohr³ (default: 0.002)")
    ap.add_argument("--percentiles", type=float, nargs=2, default=[2, 98], metavar=("LOW", "HIGH"))
    a = ap.parse_args()

    lo_all, hi_all = [], []
    for p in a.paths:
        f = esp_path(p)
        _, _, esp, _ = read_cube(f)
        lo, hi = np.percentile(esp, a.percentiles)
        print(f"== {f}")
        print(f"   grid:    min {esp.min():.6f}  max {esp.max():.6f}  mean {esp.mean():.6f}  "
              f"std {esp.std():.6f}  p{a.percentiles[0]:g}/p{a.percentiles[1]:g} {lo:.6f} / {hi:.6f}")
        dt = os.path.join(os.path.dirname(f), "Dt.cube")
        if os.path.exists(dt):
            _, _, rho, _ = read_cube(dt)
            s = surface_values(esp, rho, a.iso)
            if s.size:
                slo, shi = np.percentile(s, a.percentiles)
                lo_all.append(slo)
                hi_all.append(shi)
                print(f"   surface (density {a.iso:g}, {s.size} points): min {s.min():.6f}  max {s.max():.6f}  "
                      f"p{a.percentiles[0]:g}/p{a.percentiles[1]:g} {slo:.6f} / {shi:.6f}")
            else:
                print(f"   surface: no grid points near density {a.iso:g}")
    if len(lo_all) > 1:
        m = max(abs(min(lo_all)), abs(max(hi_all)))
        print(f"\ncommon surface range: {min(lo_all):.6f} / {max(hi_all):.6f}"
              f"   symmetric: {-m:.6f} / {m:.6f}")


if __name__ == "__main__":
    main()
