#!/usr/bin/env python3
"""Export electron density and ESP of the molecules for the page elektronenwolken.html.

Reads results/<name>/Dt.cube and ESP.cube (from esp.py), resamples them to a
coarser grid, crops the empty margin, stores the density as log-scaled bytes
and the ESP as bytes on ONE shared range for all molecules, compresses both
(gzip, base64) and writes template/site/wolken-data.js. `python3 build.py`
copies that file into the page.

Run esp.py for all molecules first, for example
    for m in water hydrogen chlorine hydrochloric_acid ammonia carbon_dioxide \\
             methane nitrogen oxygen; do python esp.py molecules/$m.xyz --overage 5; done
    python export_web.py
"""
import argparse
import base64
import gzip
import json
import os
import re

import numpy as np

from cube_tools import read_grid, surface_values

BOHR = 0.529177210903  # Å
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "..", "..", "template", "site", "wolken-data.js")

# key (as on the field page), result folder, name, formula, measured dipole moment in D
MOLECULES = [
    ("H2O", "water", "Wasser", "H₂O", 1.85),
    ("CO2", "carbon_dioxide", "Kohlenstoffdioxid", "CO₂", 0.0),
    ("H2", "hydrogen", "Wasserstoff", "H₂", 0.0),
    ("HCl", "hydrochloric_acid", "Chlorwasserstoff", "HCl", 1.08),
    ("CH4", "methane", "Methan", "CH₄", 0.0),
    ("Cl2", "chlorine", "Chlor", "Cl₂", 0.0),
    ("NH3", "ammonia", "Ammoniak", "NH₃", 1.47),
    ("N2", "nitrogen", "Stickstoff", "N₂", 0.0),
    ("O2", "oxygen", "Sauerstoff", "O₂", 0.0),
]
SYMBOL = {1: "H", 6: "C", 7: "N", 8: "O", 17: "Cl"}
LOG_MIN, LOG_MAX = -4.0, 0.0                        # density bytes: log10(ρ) from 1e-4 to 1 e/bohr³
ISO_TABLE = np.geomspace(0.0005, 0.05, 41)          # isovalues for the "share of electrons inside" table


def resample(values, step_old, step_new):
    """Trilinear resampling of a 3D grid (same origin), separable along each axis."""
    out = values
    for ax in range(3):
        n_old = out.shape[ax]
        n_new = int(np.floor((n_old - 1) * step_old[ax] / step_new)) + 1
        f = np.arange(n_new) * step_new / step_old[ax]
        i0 = np.minimum(np.floor(f).astype(int), n_old - 2)
        t = (f - i0).reshape([-1 if a == ax else 1 for a in range(3)])
        out = np.take(out, i0, axis=ax) * (1 - t) + np.take(out, i0 + 1, axis=ax) * t
    return out


def pack(arr):
    return base64.b64encode(gzip.compress(arr.astype(np.uint8).tobytes(order="C"), 9, mtime=0)).decode()


def dipole_vector(out_file):
    """Total dipole (x, y, z) in a.u. from the last 'Multipole Moments' block of a Psi4 output."""
    text = open(out_file).read()
    block = text[text.rfind("Multipole Moments"):]
    vec = []
    for ax in "XYZ":
        m = re.search(rf"Dipole {ax}\s*:\s*\S+\s+\S+\s+(\S+)", block)
        vec.append(float(m.group(1)) if m else 0.0)
    return vec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=os.path.join(HERE, "results"), help="folder with the esp.py results")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output JavaScript file")
    ap.add_argument("--step", type=float, default=0.3, help="grid spacing for the web in bohr (default: 0.3)")
    ap.add_argument("--iso", type=float, default=0.002, help="isovalue for the shared ESP range (default: 0.002)")
    ap.add_argument("--crop", type=float, default=2e-4, help="crop where the density is below this (default: 2e-4)")
    a = ap.parse_args()

    data, surf = [], []
    for key, folder, name, formula, dipole_d in MOLECULES:
        d = os.path.join(a.results, folder)
        rho_g, esp_g = read_grid(os.path.join(d, "Dt.cube")), read_grid(os.path.join(d, "ESP.cube"))
        rho, esp, step = rho_g["values"], esp_g["values"], rho_g["step"]
        n_el = sum(z for z, *_ in rho_g["atoms"])
        dv = float(np.prod(step))
        # share of electrons inside the surface = 1 - electrons outside (outside is smooth, so the grid sum is reliable)
        inside = [round(1 - float(rho[rho < iso].sum()) * dv / n_el, 4) for iso in ISO_TABLE]
        surf.append(surface_values(esp.ravel(), rho.ravel(), a.iso))

        r2, e2 = resample(rho, step, a.step), resample(esp, step, a.step)
        idx = np.argwhere(r2 >= a.crop)
        lo, hi = np.maximum(idx.min(0) - 3, 0), np.minimum(idx.max(0) + 4, r2.shape)
        r2, e2 = r2[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]], e2[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        origin = rho_g["origin"] + lo * a.step

        logr = np.clip(np.log10(np.maximum(r2, 1e-12)), LOG_MIN, LOG_MAX)
        # start orientation: rows = principal axes of the atoms (largest extent first, flat side to the viewer)
        xyz = np.array([[x, y, zc] for _, x, y, zc in rho_g["atoms"]]) * BOHR
        center = xyz.mean(0)
        evals, evecs = np.linalg.eigh((xyz - center).T @ (xyz - center) + 1e-9 * np.eye(3))
        axes = evecs[:, ::-1].T
        if np.linalg.det(axes) < 0:
            axes[2] *= -1
        data.append({
            "key": key, "name": name, "formula": formula, "dipoleD": dipole_d,
            "dipoleDir": dipole_vector(os.path.join(d, folder + ".out")),
            "atoms": [[SYMBOL[z], round(x * BOHR, 4), round(y * BOHR, 4), round(zc * BOHR, 4)] for z, x, y, zc in rho_g["atoms"]],
            "center": [round(float(v), 4) for v in center], "axes": [[round(float(v), 5) for v in row] for row in axes],
            "origin": [round(float(v) * BOHR, 5) for v in origin], "step": round(a.step * BOHR, 6),
            "shape": list(r2.shape), "electrons": n_el, "inside": inside,
            "_rho": np.round((logr - LOG_MIN) / (LOG_MAX - LOG_MIN) * 255), "_esp": e2,
        })

    allsurf = np.concatenate(surf)
    rng = float(max(abs(np.percentile(allsurf, 2)), abs(np.percentile(allsurf, 98))))
    print(f"shared ESP range ±{rng:.4f} a.u. (surface at density {a.iso:g})")
    total = 0
    for m in data:
        m["rho"] = pack(m.pop("_rho"))
        m["esp"] = pack(np.round((np.clip(m.pop("_esp"), -rng, rng) / rng + 1) * 127.5))
        size = len(m["rho"]) + len(m["esp"])
        total += size
        print(f"{m['key']:4s} grid {m['shape']}  {size / 1024:6.1f} kB  inside(0.002) {np.interp(0.002, ISO_TABLE, m['inside']):.3f}")

    payload = {"logMin": LOG_MIN, "logMax": LOG_MAX, "espRange": round(rng, 5),
               "isoTable": [round(float(v), 6) for v in ISO_TABLE], "molecules": data}
    with open(a.out, "w") as f:
        f.write("/* Erzeugt von scripts/esp/export_web.py aus Psi4-Rechnungen (B3LYP/6-31G(d)). Nicht von Hand bearbeiten. */\n")
        f.write("const WOLKEN = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"written {os.path.relpath(a.out)}: {total / 1024:.0f} kB data")


if __name__ == "__main__":
    main()
