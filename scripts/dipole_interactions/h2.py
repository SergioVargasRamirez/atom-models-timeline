#!/usr/bin/env python3
"""H2 cluster without partial charges: only weak van der Waals attraction.

Rigid H2 molecules (bond constrained to 0.074 nm) with a Lennard-Jones term on
each atom and no charges. The very small epsilon is deliberate: the molecules
hardly attract each other and stay disordered (contrast to hcl.py).

Examples:
    python h2.py
    python h2.py --n 30 --temperature 30 --steps 10000 --seed 1
"""
import numpy as np
from openmm import NonbondedForce, System
from openmm.app import Element, Topology
from openmm.unit import kilojoule_per_mole, nanometer

from md_common import base_parser, place_molecules, run

R_HH = 0.074  # nm
MASS_H = 1.008


def main():
    ap = base_parser(__doc__, temperature=50.0, timestep=0.0005)
    ap.add_argument("--box", type=float, default=3.0, help="start box edge in nm (default: 3.0)")
    ap.add_argument("--sigma", type=float, default=0.27, help="LJ sigma per atom in nm (default: 0.27)")
    ap.add_argument("--epsilon", type=float, default=0.002, help="LJ epsilon per atom in kJ/mol (default: 0.002)")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    template = np.array([[0.0, 0.0, 0.0], [R_HH, 0.0, 0.0]])
    positions = place_molecules(rng, template, a.n, a.box, min_dist=0.3)

    system = System()
    nb = NonbondedForce()  # NoCutoff by default: isolated cluster, no periodic box
    top = Topology()
    chain = top.addChain()
    H = Element.getBySymbol("H")
    for _ in range(a.n):
        i = system.addParticle(MASS_H)
        j = system.addParticle(MASS_H)
        system.addConstraint(i, j, R_HH * nanometer)
        for _ in (i, j):
            nb.addParticle(0.0, a.sigma * nanometer, a.epsilon * kilojoule_per_mole)
        nb.addException(i, j, 0.0, 1.0, 0.0)  # no LJ between the two atoms of the same molecule
        res = top.addResidue("H2", chain)
        a1 = top.addAtom("H1", H, res)
        a2 = top.addAtom("H2", H, res)
        top.addBond(a1, a2)
    system.addForce(nb)

    run("h2", top, system, positions * nanometer, a, a.temperature)


if __name__ == "__main__":
    main()
