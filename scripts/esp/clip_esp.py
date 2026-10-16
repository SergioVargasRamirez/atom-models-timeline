#!/usr/bin/env python3
"""Clip ESP cube files to a value range, so the colour scale shows the surface well.

Writes ESP_clipped.cube next to each ESP.cube. The range is either given with
--range, or taken from percentiles: of each file separately (default) or, with
--common, one range for all files so that colours can be compared between
molecules.

Percentiles of the whole grid are dominated by the large values near the nuclei.
With --iso they are taken only from the ESP values on the density isosurface
(needs Dt.cube next to ESP.cube), i.e. from the values that colour the surface.

Examples:
    python clip_esp.py results/water --range -0.0675 0.3181
    python clip_esp.py results/*/ --common
    python clip_esp.py results/*/ --common --percentiles 1 99
    python clip_esp.py results/*/ --common --iso 0.002    # recommended for comparisons
"""
import argparse
import os

import numpy as np

from cube_tools import read_cube, surface_values, write_cube


def esp_path(p):
    return os.path.join(p, "ESP.cube") if os.path.isdir(p) else p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="result folders or ESP.cube files")
    ap.add_argument("--range", type=float, nargs=2, metavar=("MIN", "MAX"), help="fixed range for all files")
    ap.add_argument("--percentiles", type=float, nargs=2, default=[2, 98], metavar=("LOW", "HIGH"),
                    help="percentile range if --range is not given (default: 2 98)")
    ap.add_argument("--common", action="store_true", help="one percentile range over all files")
    ap.add_argument("--iso", type=float, help="take percentiles of the ESP on this density isosurface (e/bohr³)")
    ap.add_argument("--suffix", default="_clipped", help="output name: ESP<suffix>.cube (default: _clipped)")
    a = ap.parse_args()

    cubes = [(esp_path(p), *read_cube(esp_path(p))) for p in a.paths]

    def basis(f, values):
        """Values the percentiles are taken from: whole grid, or surface only with --iso."""
        if a.iso is None:
            return values
        dt = os.path.join(os.path.dirname(f), "Dt.cube")
        if not os.path.exists(dt):
            ap.error(f"--iso needs {dt}")
        s = surface_values(values, read_cube(dt)[2], a.iso)
        if not s.size:
            ap.error(f"{f}: no grid points near density {a.iso:g}")
        return s

    if a.range:
        ranges = [tuple(a.range)] * len(cubes)
    elif a.common:
        allv = np.concatenate([basis(c[0], c[3]) for c in cubes])
        ranges = [tuple(np.percentile(allv, a.percentiles))] * len(cubes)
    else:
        ranges = [tuple(np.percentile(basis(c[0], c[3]), a.percentiles)) for c in cubes]

    for (f, header, atoms, values, shape), (lo, hi) in zip(cubes, ranges):
        base, ext = os.path.splitext(f)
        out = base + a.suffix + ext
        write_cube(out, header, atoms, np.clip(values, lo, hi), shape)
        print(f"{out}: clipped to {lo:.6f} / {hi:.6f}")


if __name__ == "__main__":
    main()
