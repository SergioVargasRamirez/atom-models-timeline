"""Liquid water (TIP4P-Ew, 293 K, 1 bar) with N molecules, scaled to the box of the ice block; snapshot as JSON.

Usage (openmm env): python make_liquid.py ice.json 103 > liquid.json
"""
import json, sys
import numpy as np
from openmm import LangevinMiddleIntegrator, MonteCarloBarostat, Vec3
from openmm.app import ForceField, Modeller, PME, HBonds, Simulation, Topology
from openmm.unit import nanometer, kelvin, picosecond, bar, angstrom

box = np.array(json.load(open(sys.argv[1]))["box"])   # Å, from the ice block
ff = ForceField("tip4pew.xml")
mod = Modeller(Topology(), [])
NWANT = int(sys.argv[2]) if len(sys.argv) > 2 else 103
mod.addSolvent(ff, model="tip4pew", boxSize=Vec3(*(box * 1.06 / 10)) * nanometer)
extra = list(mod.topology.residues())[NWANT:]
assert len(list(mod.topology.residues())) >= NWANT, "box too small"
mod.delete(extra)
system = ff.createSystem(mod.topology, nonbondedMethod=PME, nonbondedCutoff=0.6 * nanometer, constraints=HBonds, rigidWater=True)
system.addForce(MonteCarloBarostat(1 * bar, 293 * kelvin))
integ = LangevinMiddleIntegrator(293 * kelvin, 1 / picosecond, 0.002 * picosecond)
integ.setRandomNumberSeed(7)
sim = Simulation(mod.topology, system, integ)
sim.context.setPositions(mod.positions)
sim.minimizeEnergy()
sim.context.setVelocitiesToTemperature(293 * kelvin, 7)
sim.step(50000)          # 100 ps at 1 bar: the box shrinks to the density of liquid water
state = sim.context.getState(getPositions=True)
pos = state.getPositions(asNumpy=True).value_in_unit(angstrom)
Lnpt = np.array(state.getPeriodicBoxVectors(asNumpy=True).value_in_unit(angstrom)).diagonal()
print(f"after NPT: box {Lnpt.round(2)} Å, density {NWANT * 18.015 / 6.02214076e23 / (np.prod(Lnpt) * 1e-24):.3f} g/cm³", file=sys.stderr)
scale = box / Lnpt                                # scale the whole box (less than a few %) to the ice box for display
pos = pos * scale; L = box
mols = []
for res in mod.topology.residues():
    at = {a.name: pos[a.index] for a in res.atoms()}
    o = at["O"]; shift = -L * np.floor(o / L)      # put the O into the box, keep the molecule whole
    mols.append({"O": (o + shift).round(3).tolist(), "H": [(at[h] + shift).round(3).tolist() for h in ("H1", "H2")]})
# geometric H-bonds: O···O < 3.5 Å and angle H–O(donor)···O(acceptor) < 30°
O = np.array([m["O"] for m in mols]); mic = lambda d: d - L * np.round(d / L)
hb = []
for i, m in enumerate(mols):
    for h in m["H"]:
        vh = mic(np.array(h) - O[i])
        for j in range(len(mols)):
            if j == i: continue
            d = mic(O[j] - O[i]); r = np.linalg.norm(d)
            if r < 3.5 and np.degrees(np.arccos(vh @ d / (np.linalg.norm(vh) * r))) < 30:
                hb.append([min(i, j), max(i, j)])
dens = len(mols) * 18.015 / 6.02214076e23 / (np.prod(L) * 1e-24)
print(f"{len(mols)} molecules, box {L.round(2)} Å, density {dens:.3f} g/cm³, H-bonds per molecule {2 * len(hb) / len(mols):.2f}", file=sys.stderr)
json.dump({"box": L.round(3).tolist(), "molecules": mols, "hbonds": hb}, sys.stdout)
