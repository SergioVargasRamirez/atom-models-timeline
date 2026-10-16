"""Shared parts of the OpenMM cluster simulations (h2.py, hcl.py, h2o.py)."""
import argparse
import os
import sys

import numpy as np
from openmm import LangevinIntegrator
from openmm.app import DCDReporter, PDBFile, Simulation, StateDataReporter
from openmm.unit import kelvin, kilojoule_per_mole, nanometer, picoseconds


def base_parser(doc, n=20, temperature=300.0, timestep=0.002, steps=5000):
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=n, help=f"number of molecules (default: {n})")
    ap.add_argument("--temperature", type=float, default=temperature, help=f"K (default: {temperature:g})")
    ap.add_argument("--timestep", type=float, default=timestep, help=f"ps (default: {timestep:g})")
    ap.add_argument("--steps", type=int, default=steps, help=f"MD steps (default: {steps})")
    ap.add_argument("--report", type=int, default=50, help="write a DCD frame every N steps (default: 50)")
    ap.add_argument("--seed", type=int, help="random seed for start positions and thermostat")
    ap.add_argument("--outdir", help="output folder (default: results/<name>)")
    return ap


def random_rotation(rng):
    """Uniformly random rotation matrix (Shoemake's method)."""
    u1, u2, u3 = rng.random(3)
    w, x, y, z = (np.sqrt(1 - u1) * np.sin(2 * np.pi * u2), np.sqrt(1 - u1) * np.cos(2 * np.pi * u2),
                  np.sqrt(u1) * np.sin(2 * np.pi * u3), np.sqrt(u1) * np.cos(2 * np.pi * u3))
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def place_molecules(rng, template, n, box, min_dist, max_tries=100000):
    """Random positions (nm) for n copies of template (atoms × 3, nm) in a cubic box.

    Every atom of a new molecule keeps at least min_dist from every atom placed before.
    """
    placed = np.empty((0, 3))
    for _ in range(n):
        for _ in range(max_tries):
            mol = template @ random_rotation(rng).T + rng.uniform(0, box, 3)
            if placed.size == 0 or np.min(np.linalg.norm(placed[:, None, :] - mol[None, :, :], axis=2)) > min_dist:
                placed = np.vstack([placed, mol])
                break
        else:
            sys.exit(f"Could not place {n} molecules in a {box} nm box with {min_dist} nm spacing. "
                     f"Use a larger --box or fewer --n.")
    return placed


def run(name, topology, system, positions, a, temperature):
    """Minimize, write <name>_initial.pdb, run MD with DCD + log, write <name>_final.pdb."""
    outdir = os.path.abspath(a.outdir or os.path.join("results", name))
    os.makedirs(outdir, exist_ok=True)
    out = lambda suffix: os.path.join(outdir, name + suffix)

    integrator = LangevinIntegrator(temperature * kelvin, 1 / picoseconds, a.timestep * picoseconds)
    if a.seed is not None:
        integrator.setRandomNumberSeed(a.seed)
    sim = Simulation(topology, system, integrator)
    sim.context.setPositions(positions)
    sim.minimizeEnergy(tolerance=1 * kilojoule_per_mole / nanometer, maxIterations=1000)
    if a.seed is not None:
        sim.context.setVelocitiesToTemperature(temperature * kelvin, a.seed)
    else:
        sim.context.setVelocitiesToTemperature(temperature * kelvin)

    def save(suffix):
        with open(out(suffix), "w") as f:
            PDBFile.writeFile(topology, sim.context.getState(getPositions=True).getPositions(), f)

    save("_initial.pdb")  # minimized start structure
    log_kw = dict(step=True, potentialEnergy=True, kineticEnergy=True, totalEnergy=True, temperature=True)
    sim.reporters.append(StateDataReporter(sys.stdout, max(a.steps // 10, 1), **log_kw))
    sim.reporters.append(StateDataReporter(out(".csv"), a.report, **log_kw))
    sim.reporters.append(DCDReporter(out(".dcd"), a.report))
    sim.step(a.steps)
    save("_final.pdb")
    print(f"written to {outdir}: {name}_initial.pdb, {name}.dcd, {name}_final.pdb, {name}.csv")
