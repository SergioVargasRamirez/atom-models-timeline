#!/usr/bin/env python3
"""Butane polarized by a nearby point charge (induced dipole), with Psi4.

A point charge (an ion, not a dipole) sits next to one end of a butane
molecule and pulls on its electron cloud. With --pair a second butane is
added further away for comparison: it barely feels the charge.

Writes Dt.cube and ESP.cube plus the Psi4 output. The ESP cube contains the
potential of the molecule(s) only, not that of the point charge.

Examples:
    python butane_point_charge.py                          # one butane, +0.5 at (0, 5.5, 0) Å
    python butane_point_charge.py --pair --charge 1.5      # two butanes, +1.5
    python butane_point_charge.py --pos 0 6 0 --method hf  # like the original HF runs
"""
import argparse
import os
import sys

import numpy as np

ANG2BOHR = 1.8897259886

# anti-butane, optimized (HF/6-31G(d)); long axis along y
BUTANE = """\
C   -0.012986703207    1.976022235746    0.000000042018
C   -0.552101627617    0.530708705243   -0.000000073016
C    0.552169703683   -0.530744754274   -0.000000036630
C    0.012876438145   -1.975936616853    0.000000051395
H    1.072747093954    1.994720523983    0.000000008086
H   -0.341764766414    2.528785540687    0.873732047701
H   -0.341764795645    2.528785668716   -0.873731870352
H   -1.187981716998    0.371795933162    0.867053478744
H   -1.187981807980    0.371795959682   -0.867053563789
H    1.188140836367   -0.372065628832    0.867024443326
H    1.188140845321   -0.372065692870   -0.867024518341
H   -1.072866104658   -1.994780162703   -0.000000009151
H    0.341916350149   -2.528781138677    0.873634643331
H    0.341916403046   -2.528781222998   -0.873634466269"""


def shifted(xyz, dx):
    out = []
    for line in xyz.splitlines():
        s, x, y, z = line.split()
        out.append((s, float(x) + dx, float(y), float(z)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--charge", type=float, default=0.5, help="point charge in e (default: +0.5)")
    ap.add_argument("--pos", type=float, nargs=3, default=[0.0, 5.5, 0.0], metavar=("X", "Y", "Z"),
                    help="position of the point charge in Å (default: 0 5.5 0, about 3.1 Å from the nearest H)")
    ap.add_argument("--pair", action="store_true", help="add a second butane, shifted along x")
    ap.add_argument("--shift", type=float, default=6.0, help="x shift of the second butane in Å (default: 6.0)")
    ap.add_argument("--min-dist", type=float, default=2.5,
                    help="refuse to run if the charge is closer than this to an atom, in Å (default: 2.5)")
    ap.add_argument("--method", default="b3lyp", help="default: b3lyp (the original runs used hf)")
    ap.add_argument("--basis", default="6-31G(d)")
    ap.add_argument("--spacing", type=float, default=0.2, help="cube grid spacing in bohr (default: 0.2)")
    ap.add_argument("--outdir", help="default: results/butane_point_charge or results/butane_pair_point_charge")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--memory", default="2 GB")
    a = ap.parse_args()

    frags = [shifted(BUTANE, 0.0)]
    if a.pair:
        frags.append(shifted(BUTANE, a.shift))

    pos = np.array(a.pos)
    coords = np.array([[x, y, z] for f in frags for _, x, y, z in f])
    dmin = np.linalg.norm(coords - pos, axis=1).min()
    print(f"point charge {a.charge:+g} e at {tuple(a.pos)} Å, nearest atom {dmin:.2f} Å away")
    if dmin < a.min_dist:
        sys.exit(f"Charge is inside the electron cloud ({dmin:.2f} Å < {a.min_dist} Å). "
                 f"Move it further away or lower --min-dist.")

    name = "butane_pair_point_charge" if a.pair else "butane_point_charge"
    outdir = os.path.abspath(a.outdir or os.path.join("results", name))
    os.makedirs(outdir, exist_ok=True)
    os.chdir(outdir)  # Psi4 writes timer.dat etc. into the working directory

    import psi4

    psi4.set_memory(a.memory)
    psi4.set_num_threads(a.threads)
    psi4.set_output_file(os.path.join(outdir, name + ".out"), False)
    psi4.core.IOManager.shared_object().set_default_path(outdir)

    blocks = ["0 1\n" + "\n".join(f"{s} {x:.6f} {y:.6f} {z:.6f}" for s, x, y, z in f) for f in frags]
    # keep the input frame, otherwise the molecule could move relative to the point charge
    mol = psi4.geometry("\n--\n".join(blocks) + "\nsymmetry c1\nno_com\nno_reorient\n", name=name)

    psi4.set_options({
        "basis": a.basis,
        "cubeprop_tasks": ["esp"],
        "cubeprop_filepath": outdir,
        "cubic_grid_spacing": [a.spacing] * 3,
        "maxiter": 200,
    })
    charges = [[a.charge, (pos * ANG2BOHR).tolist()]]  # Psi4 expects bohr
    energy, wfn = psi4.energy(a.method, molecule=mol, return_wfn=True, external_potentials=charges)
    psi4.cubeprop(wfn)

    with open(os.path.join(outdir, "point_charge.txt"), "w") as f:
        f.write(f"charge_e {a.charge}\nposition_angstrom {a.pos[0]} {a.pos[1]} {a.pos[2]}\n")
    print(f"{name}: {a.method}/{a.basis}, E = {energy:.8f} Eh, written to {outdir}")


if __name__ == "__main__":
    main()
