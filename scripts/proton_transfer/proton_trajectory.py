#!/usr/bin/env python3
"""Proton transfer from acetic acid to water: snapshots for an animation.

Start: acetic acid (B3LYP/6-31G(d) optimized) with a water molecule hydrogen
bonded to its O-H group. The proton moves in a straight line along the O···O
axis, from its O-H bond in the acid (0.976 Å) to an O-H bond in H3O+
(--oh-end, default 0.975 Å from the water O). All other atoms stay fixed, so
this is a scan, not a computed reaction path.

The energies (--energies) are for the gas phase with ONE water molecule. There
the transfer is strongly uphill (about +200 kJ/mol), because nothing stabilizes
the ion pair CH3COO- + H3O+. In aqueous solution, the surrounding water
molecules stabilize the ions and the reaction runs (pKa 4.76).

With --energies, Psi4 computes a single-point energy for every step
(energies.csv), which gives the energy profile of the scan.

Writes into --outdir:
    snapshot_XX.xyz    whole system per step
    proton_XX.xyz      the moving proton only
    trajectory.xyz     all steps in one multi-frame file (VMD, Jmol)
    energies.csv       only with --energies

Examples:
    python proton_trajectory.py
    python proton_trajectory.py --steps 30 --d-oo 2.55
    python proton_trajectory.py --energies --method b3lyp --basis 6-31+G(d)
"""
import argparse
import os

import numpy as np

# acetic acid, B3LYP/6-31G(d) optimized (Å); the last H is the acidic proton
ACID = [
    ("C", -1.461718182949, 0.037015453212, 0.0),
    ("C", 0.045263932959, 0.099194134657, 0.0),
    ("O", 0.718993639550, 1.104369604780, 0.0),   # C=O
    ("O", 0.591771291064, -1.144877065560, 0.0),  # O-H, donates the proton
    ("H", -1.867829444918, 1.048631304655, 0.0),
    ("H", -1.813935292783, -0.507834075061, 0.882031836800),
    ("H", -1.813935292783, -0.507834075061, -0.882031836800),
    ("H", 1.558387476505, -1.011904584099, 0.0),  # acidic proton
]
O_ACID, PROTON = 3, 7
R_OH_WATER = 0.957  # Å
HOH_WATER = 104.5   # degrees


def build_system(d_oo, tilt):
    """Acetic acid + water, water O on the O-H axis at d_oo from the acid O.

    The water's H atoms point away from the acid, its H-O-H bisector tilted by
    `tilt` degrees from the O···O axis, so its free lone pair faces the proton.
    """
    sym = [s for s, *_ in ACID]
    xyz = np.array([c for _, *c in ACID])
    o_a, h = xyz[O_ACID], xyz[PROTON]
    u = (h - o_a) / np.linalg.norm(h - o_a)        # O···O axis
    z = np.array([0.0, 0.0, 1.0])                  # normal of the acid plane
    v = np.cross(z, u)                             # in plane, perpendicular to u
    o_w = o_a + d_oo * u
    b = np.cos(np.radians(tilt)) * u + np.sin(np.radians(tilt)) * v
    half = np.radians(HOH_WATER / 2)
    h_w1 = o_w + R_OH_WATER * (np.cos(half) * b + np.sin(half) * z)
    h_w2 = o_w + R_OH_WATER * (np.cos(half) * b - np.sin(half) * z)
    return sym + ["O", "H", "H"], np.vstack([xyz, o_w, h_w1, h_w2]), u


def write_xyz(f, sym, xyz, comment):
    f.write(f"{len(sym)}\n{comment}\n")
    for s, (x, y, zc) in zip(sym, xyz):
        f.write(f"{s} {x:.6f} {y:.6f} {zc:.6f}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", type=int, default=15, help="number of snapshots (default: 15)")
    ap.add_argument("--d-oo", type=float, default=2.65, help="O···O distance in Å (default: 2.65, hydrogen bond)")
    ap.add_argument("--oh-end", type=float, default=0.975, help="final O-H distance in H3O+ in Å (default: 0.975)")
    ap.add_argument("--tilt", type=float, default=48.0,
                    help="tilt of the water's H-O-H bisector from the O···O axis in degrees (default: 48)")
    ap.add_argument("--outdir", default=os.path.join("results", "proton_transfer"))
    ap.add_argument("--energies", action="store_true", help="single-point Psi4 energy for every step")
    ap.add_argument("--method", default="b3lyp")
    ap.add_argument("--basis", default="6-31G(d)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--memory", default="2 GB")
    a = ap.parse_args()

    sym, xyz, u = build_system(a.d_oo, a.tilt)
    o_a, o_w = xyz[O_ACID], xyz[-3]
    start = xyz[PROTON].copy()
    end = o_w - a.oh_end * u
    if np.linalg.norm(end - o_a) <= np.linalg.norm(start - o_a):
        ap.error("--d-oo too short: the end point lies before the start point")
    a.outdir = os.path.abspath(a.outdir)
    os.makedirs(a.outdir, exist_ok=True)

    frames = []
    with open(os.path.join(a.outdir, "trajectory.xyz"), "w") as traj:
        for i, t in enumerate(np.linspace(0.0, 1.0, a.steps)):
            frame = xyz.copy()
            frame[PROTON] = start + t * (end - start)
            d_a = np.linalg.norm(frame[PROTON] - o_a)
            d_w = np.linalg.norm(frame[PROTON] - o_w)
            comment = f"Step {i + 1}  O(acid)-H {d_a:.3f} A  H-O(water) {d_w:.3f} A"
            with open(os.path.join(a.outdir, f"snapshot_{i + 1:02d}.xyz"), "w") as f:
                write_xyz(f, sym, frame, comment)
            with open(os.path.join(a.outdir, f"proton_{i + 1:02d}.xyz"), "w") as f:
                write_xyz(f, ["H"], frame[[PROTON]], comment)
            write_xyz(traj, sym, frame, comment)
            frames.append((frame, d_a, d_w))
    print(f"{a.steps} snapshots in {a.outdir}: O(acid)-H {np.linalg.norm(start - o_a):.3f} -> "
          f"{np.linalg.norm(end - o_a):.3f} Å, H-O(water) {np.linalg.norm(start - o_w):.3f} -> {a.oh_end:.3f} Å")

    if a.energies:
        os.chdir(a.outdir)  # Psi4 writes timer.dat etc. into the working directory
        import psi4

        psi4.set_memory(a.memory)
        psi4.set_num_threads(a.threads)
        psi4.set_output_file(os.path.join(a.outdir, "energies.out"), False)
        psi4.set_options({"basis": a.basis})
        rows = []
        for i, (frame, d_a, d_w) in enumerate(frames):
            geom = "0 1\n" + "\n".join(f"{s} {x:.6f} {y:.6f} {zc:.6f}" for s, (x, y, zc) in zip(sym, frame))
            mol = psi4.geometry(geom + "\nsymmetry c1\nno_com\nno_reorient\n", name=f"step{i + 1:02d}")
            e = psi4.energy(a.method, molecule=mol)
            rows.append((i + 1, d_a, d_w, e))
            psi4.core.clean()
        e0 = rows[0][3]
        with open(os.path.join(a.outdir, "energies.csv"), "w") as f:
            f.write("step,d_OacidH_A,d_HOwater_A,energy_Eh,relative_kJ_mol\n")
            for step, d_a, d_w, e in rows:
                f.write(f"{step},{d_a:.4f},{d_w:.4f},{e:.8f},{(e - e0) * 2625.4996:.2f}\n")
                print(f"step {step:2d}  O-H {d_a:.3f} Å  H-O(w) {d_w:.3f} Å  ΔE {(e - e0) * 2625.4996:8.2f} kJ/mol")


if __name__ == "__main__":
    main()
