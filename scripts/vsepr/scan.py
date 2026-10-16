#!/usr/bin/env python3
"""Relaxed angle scan (MP2/aug-cc-pVTZ): energy vs. angle between the lower H atoms.

At every angle the X–H bond length is relaxed (parabola through three points).
Usage (psi4 env): python scan.py H2O results/H2O_scan.json [--threads 8]
"""
import argparse, json, os, time
import numpy as np
import psi4
from geometry import psi4_string

HARTREE_KJ = 2625.4996
ANGLES = {"H2O": list(range(60, 181, 5)), "NH3": [90 + 2 * k for k in range(16)], "CH4": [90 + 2 * k for k in range(16)]}
R0 = {"H2O": 0.959, "NH3": 1.010, "CH4": 1.088}

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("name", choices=list(ANGLES)); ap.add_argument("out")
ap.add_argument("--threads", type=int, default=8); ap.add_argument("--method", default="mp2"); ap.add_argument("--basis", default="aug-cc-pvtz")
a = ap.parse_args()
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
psi4.set_memory("6 GB"); psi4.set_num_threads(a.threads); psi4.core.set_output_file(a.out + ".log", False)
psi4.set_options({"basis": a.basis, "scf_type": "df", "mp2_type": "df", "e_convergence": 1e-8, "d_convergence": 1e-8})

def energy(ang, r):
    e = psi4.energy(a.method, molecule=psi4.geometry(psi4_string(a.name, ang, r))); psi4.core.clean(); return e

rows, r0, dr, t0 = [], R0[a.name], 0.03, time.time()
for ang in ANGLES[a.name]:
    rs = [r0 - dr, r0, r0 + dr]; c = np.polyfit(rs, [energy(ang, r) for r in rs], 2)
    rmin = -c[1] / (2 * c[0]); rows.append((ang, float(rmin), float(np.polyval(c, rmin)))); r0 = rmin
    print(f"{a.name} {ang:6.1f}°  r {rmin:.4f} Å  ({time.time() - t0:.0f} s)", flush=True)
emin = min(e for *_, e in rows)
with open(a.out, "w") as f:
    json.dump({"name": a.name, "method": f"{a.method}/{a.basis}", "angle": [x for x, _, _ in rows],
               "r": [round(r, 4) for _, r, _ in rows], "dE_kJ": [round((e - emin) * HARTREE_KJ, 3) for *_, e in rows]}, f)
