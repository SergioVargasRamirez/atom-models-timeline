#!/usr/bin/env python3
"""HCl cluster: dipole-dipole attraction lines the molecules up (H next to Cl).

Rigid HCl molecules (bond constrained to 0.127 nm) with partial charges and
Lennard-Jones terms.

The default partial charges of ±0.4 e are exaggerated ON PURPOSE, for the
lesson on dipole-dipole interactions: they give 2.4 D instead of the measured
1.08 D (realistic: ±0.18 e, --charge 0.18), so the alignment of the molecules
shows clearly.

Examples:
    python hcl.py
    python hcl.py --charge 0.18        # realistic dipole, for comparison
    python hcl.py --temperature 100 --steps 20000 --seed 1
"""
import numpy as np
from openmm import NonbondedForce, System
from openmm.app import Element, Topology
from openmm.unit import kilojoule_per_mole, nanometer

from md_common import base_parser, place_molecules, run

R_HCL = 0.127  # nm
MASS_H, MASS_CL = 1.008, 35.45
SIGMA_H, EPS_H = 0.27, 0.02  # nm, kJ/mol
SIGMA_CL, EPS_CL = 0.33, 0.5


def main():
    ap = base_parser(__doc__, temperature=20.0, timestep=0.0005)
    ap.add_argument("--charge", type=float, default=0.4,
                    help="partial charge q: H gets +q, Cl gets -q (default: 0.4, exaggerated; realistic 0.18)")
    ap.add_argument("--box", type=float, default=1.5, help="start box edge in nm (default: 1.5)")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    template = np.array([[0.0, 0.0, 0.0], [R_HCL, 0.0, 0.0]])
    positions = place_molecules(rng, template, a.n, a.box, min_dist=0.3)

    system = System()
    nb = NonbondedForce()  # NoCutoff by default: isolated cluster, no periodic box
    top = Topology()
    chain = top.addChain()
    H, Cl = Element.getBySymbol("H"), Element.getBySymbol("Cl")
    for _ in range(a.n):
        i = system.addParticle(MASS_H)
        j = system.addParticle(MASS_CL)
        system.addConstraint(i, j, R_HCL * nanometer)
        nb.addParticle(+a.charge, SIGMA_H * nanometer, EPS_H * kilojoule_per_mole)
        nb.addParticle(-a.charge, SIGMA_CL * nanometer, EPS_CL * kilojoule_per_mole)
        nb.addException(i, j, 0.0, 1.0, 0.0)  # no Coulomb/LJ inside the same molecule
        res = top.addResidue("HCl", chain)
        a1 = top.addAtom("H", H, res)
        a2 = top.addAtom("Cl", Cl, res)
        top.addBond(a1, a2)
    system.addForce(nb)

    print(f"partial charges ±{a.charge:g} e -> dipole {a.charge * R_HCL / 0.020819:.2f} D (measured: 1.08 D)")
    run("hcl", top, system, positions * nanometer, a, a.temperature)


if __name__ == "__main__":
    main()
