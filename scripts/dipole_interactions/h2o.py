#!/usr/bin/env python3
"""Water cluster with the TIP3P model: hydrogen bonds between the molecules.

Rigid TIP3P water (OpenMM's built-in tip3p.xml). The molecules start in a small
pre-equilibrated box and form a hydrogen-bonded cluster in vacuum. Above about
300 K single molecules may evaporate from the cluster.

Examples:
    python h2o.py
    python h2o.py --n 40 --temperature 250 --steps 20000
"""
from openmm.app import ForceField, HBonds, Modeller, NoCutoff, Topology

from md_common import base_parser, run


def main():
    ap = base_parser(__doc__, temperature=300.0, timestep=0.002)
    a = ap.parse_args()

    forcefield = ForceField("tip3p.xml")
    modeller = Modeller(Topology(), [])
    modeller.addSolvent(forcefield, model="tip3p", numAdded=a.n)

    system = forcefield.createSystem(modeller.topology, nonbondedMethod=NoCutoff,
                                     constraints=HBonds, rigidWater=True)
    run("h2o", modeller.topology, system, modeller.positions, a, a.temperature)


if __name__ == "__main__":
    main()
