#!/usr/bin/env python3
"""Localized orbitals (Boys, B3LYP/cc-pVTZ) at the most stable angle of a scan: cube files and measures.

For every electron pair: kind (core, bond, lone pair), distance of its centroid from the central
atom, spread (size) and spread/distance (how much angle it takes up around the central atom).
Usage (psi4 env): python lmo.py results/H2O_scan.json results/H2O_lmo
"""
import argparse, json, os
import numpy as np
import psi4
from geometry import psi4_string

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("scan"); ap.add_argument("outdir"); ap.add_argument("--threads", type=int, default=8)
a = ap.parse_args()
scan = json.load(open(a.scan)); name = scan["name"]
ang, E, R = np.array(scan["angle"], float), np.array(scan["dE_kJ"]), np.array(scan["r"])
i = int(np.argmin(E)); j = min(max(i, 1), len(ang) - 2)
c = np.polyfit(ang[j - 1:j + 2], E[j - 1:j + 2], 2); amin = float(-c[1] / (2 * c[0]))
if name == "CH4": amin = float(np.degrees(np.arccos(-1 / 3)))          # exact by symmetry
rmin = float(np.interp(amin, ang, R))
os.makedirs(a.outdir, exist_ok=True); os.chdir(a.outdir)
psi4.set_memory("4 GB"); psi4.set_num_threads(a.threads); psi4.core.set_output_file("lmo.log", False)
psi4.set_options({"basis": "cc-pvtz", "scf_type": "df", "cubeprop_tasks": ["orbitals"], "cubic_grid_spacing": [0.2] * 3, "cubic_grid_overage": [4.0] * 3})
m = psi4.geometry(psi4_string(name, amin, rmin))
_, wfn = psi4.energy("b3lyp", molecule=m, return_wfn=True)
nocc = wfn.nalpha(); C = wfn.Ca_subset("AO", "OCC")
loc = psi4.core.Localizer.build("BOYS", wfn.basisset(), C); loc.localize(); L = loc.L
wfn.Ca().np[:, :nocc] = L.np                                          # C1 symmetry: AO == SO
mints = psi4.core.MintsHelper(wfn.basisset())
dip = [np.asarray(x) for x in mints.ao_dipole()]; quad = [np.asarray(x) for x in mints.ao_quadrupole()]
xyz = np.array(m.geometry().np); B = 0.529177210903
pairs = []
for k in range(nocc):
    v = L.np[:, k]; cen = np.array([-(v @ d @ v) for d in dip])
    r2 = -(v @ quad[0] @ v) - (v @ quad[3] @ v) - (v @ quad[5] @ v); spread = float(np.sqrt(max(0.0, r2 - cen @ cen)) * B)
    dist = [float(np.linalg.norm(cen - p) * B) for p in xyz]
    kind = "core" if dist[0] < 0.1 else ("bond" if min(dist[1:]) < 0.75 else "lone")
    pairs.append({"index": k + 1, "kind": kind, "dist": round(dist[0], 3), "spread": round(spread, 3), "angular": round(spread / dist[0], 2) if dist[0] > 0.1 else None})
psi4.set_options({"cubeprop_orbitals": list(range(1, nocc + 1))}); psi4.cubeprop(wfn)
json.dump({"name": name, "angle": round(amin, 2), "r": round(rmin, 4), "pairs": pairs}, open("lmo.json", "w"), indent=1)
for p in pairs: print(name, p)
