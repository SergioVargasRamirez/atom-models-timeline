#!/usr/bin/env python3
"""Relaxed torsion scan Cl–C–C–Cl for 1,2-dichloroethane (single bond) and 1,2-dichloroethene
(double bond), plus the linear 1,2-dichloroethyne; energy, dipole moment and geometry per point.

The dihedral is frozen (for ethene also H–C–C–H), everything else is optimized (B3LYP/def2-TZVP). Each point starts from
the previous optimized geometry with the far half turned by one step (starting from the rough
Z-matrix lets the optimizer wander off on twisted ethene). Twisted ethene is a diradical: the
double bond is therefore computed unrestricted with a mixed guess (broken symmetry), otherwise
the barrier comes out far too high. Finished points are kept in <out>.partial.json, so an
interrupted scan resumes where it stopped. --reverse scans from 180° down (for points that only
converge when approached from the E side).
Usage (psi4 env): python scan_torsion.py ethane results/ethane.json [--step 10] [--threads 8]
"""
import argparse, json, os
import numpy as np
import psi4

ZMAT = {
    "ethane": """0 1
C
C 1 1.52
Cl 1 1.80 2 110.0
Cl 2 1.80 1 110.0 3 {phi}
H 1 1.09 2 110.0 3 120.0
H 1 1.09 2 110.0 3 -120.0
H 2 1.09 1 110.0 4 120.0
H 2 1.09 1 110.0 4 -120.0
symmetry c1""",
    "ethene": """0 1
C
C 1 1.33
Cl 1 1.73 2 122.0
Cl 2 1.73 1 122.0 3 {phi}
H 1 1.08 2 122.0 3 180.0
H 2 1.08 1 122.0 4 180.0
symmetry c1""",
    "ethyne": """0 1
C
C 1 1.20
X 1 1.0 2 90.0
Cl 1 1.63 3 90.0 2 180.0
Cl 2 1.63 3 90.0 1 180.0
symmetry c1""",
}
DEBYE = 2.541746
FAR = {"ethane": [3, 6, 7], "ethene": [3, 5]}   # atoms on C2 that turn with the dihedral
# Frozen dihedrals (1-based). For ethene H–C–C–H is frozen too: with Cl–C–C–Cl alone the CHCl ends
# pyramidalize, the π bond twists less than the dihedral says, and the scan snaps over past 90°.
FROZEN = {"ethane": "3 1 2 4", "ethene": "3 1 2 4 5 1 2 6"}

def dihedral(p0, p1, p2, p3):
    b0, b1, b2 = p0 - p1, p2 - p1, p3 - p2
    b1 = b1 / np.linalg.norm(b1); v = b0 - (b0 @ b1) * b1; w = b2 - (b2 @ b1) * b1
    return np.degrees(np.arctan2(np.cross(b1, v) @ w, v @ w))

def turned(xyz, name, phi):
    """Previous geometry (in frame(): C–C along x) with the far half turned to |dihedral| = phi."""
    for sign in (1, -1):
        out = xyz.copy(); cur = abs(dihedral(*xyz[[2, 0, 1, 3]]))
        a = np.radians(sign * (phi - cur)); c, s = np.cos(a), np.sin(a)
        rot = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        out[FAR[name]] = (xyz[FAR[name]] - xyz[1]) @ rot.T + xyz[1]
        if abs(abs(dihedral(*out[[2, 0, 1, 3]])) - phi) < 1e-3: return out
    raise RuntimeError("could not set the dihedral")

def frame(xyz):
    """C1 at the origin, C2 on +x, the first Cl in the xy plane (y > 0)."""
    x = xyz[1] - xyz[0]; x /= np.linalg.norm(x)
    v = xyz[2] - xyz[0]; y = v - (v @ x) * x; y /= np.linalg.norm(y); z = np.cross(x, y)
    return (xyz - xyz[0]) @ np.array([x, y, z]).T

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("name", choices=list(ZMAT)); ap.add_argument("out")
ap.add_argument("--step", type=float, default=10); ap.add_argument("--reverse", action="store_true", help="scan from 180° down")
ap.add_argument("--threads", type=int, default=8)
a = ap.parse_args()
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
psi4.set_memory("6 GB"); psi4.set_num_threads(a.threads); psi4.core.set_output_file(a.out + ".log", False)
opts = {"basis": "def2-tzvp", "scf_type": "df", "g_convergence": "gau", "geom_maxiter": 150,
        "intrafrag_step_limit": 0.15, "intrafrag_step_limit_max": 0.3}
if a.name == "ethene": opts.update({"reference": "uks", "guess_mix": True})
psi4.set_options(opts)

phis = [None] if a.name == "ethyne" else list(np.arange(0, 180 + 1e-9, a.step))[::-1 if a.reverse else 1]
partial = a.out + ".partial.json"
rows = json.load(open(partial)) if os.path.exists(partial) else []
for phi in phis:
    if any(r["phi"] == (None if phi is None else float(phi)) for r in rows): continue
    # nearest finished point; on a tie the most recent one (the direction the scan comes from)
    near = min(reversed(rows), key=lambda r: abs(r["phi"] - phi)) if rows and phi is not None else None
    if near and abs(near["phi"] - phi) <= a.step + 1e-6:   # start from the neighbouring point, turned by one step
        prev = turned(np.array([p[1:] for p in near["atoms"]]), a.name, phi)
        syms = [p[0] for p in near["atoms"]]
        m = psi4.geometry("0 1\n" + "\n".join(f"{s} {x:.6f} {y:.6f} {z:.6f}" for s, (x, y, z) in zip(syms, prev)) +
                          "\nsymmetry c1\nno_reorient\nno_com")
    else:
        m = psi4.geometry(ZMAT[a.name].format(phi=phi if phi is not None else 0))
    if phi is not None: psi4.set_options({"optking__frozen_dihedral": FROZEN[a.name]})
    e, wfn = psi4.optimize("b3lyp", molecule=m, return_wfn=True)
    mu = np.linalg.norm(np.asarray(wfn.variable("CURRENT DIPOLE"))) * DEBYE
    xyz = np.array(m.geometry().np) * psi4.constants.bohr2angstroms
    syms = [m.symbol(i).capitalize() for i in range(m.natom())]
    rows.append({"phi": None if phi is None else float(phi), "E": float(e), "mu": round(float(mu), 3),
                 "atoms": [[s, *[round(float(c), 4) for c in p]] for s, p in zip(syms, frame(xyz))]})
    print(f"{a.name} phi {phi}: E {e:.6f} Eh, dipole {mu:.2f} D", flush=True)
    json.dump(rows, open(partial, "w"))
    psi4.core.clean()
rows.sort(key=lambda r: -1 if r["phi"] is None else r["phi"])
emin = min(r["E"] for r in rows)
for r in rows: r["dE"] = round((r.pop("E") - emin) * 2625.4996, 3)
os.remove(partial)
json.dump({"name": a.name, "method": "B3LYP/def2-TZVP" + (" (UKS, broken symmetry)" if a.name == "ethene" else ""), "points": rows}, open(a.out, "w"))
