#!/usr/bin/env python3
"""Electron density and electrostatic potential (ESP) of one molecule with Psi4.

Writes Dt.cube (total electron density) and ESP.cube (electrostatic potential)
plus the Psi4 output into one folder per molecule.

The molecule comes from an .xyz file. Its comment line (line 2) may set
defaults as key=value pairs, for example

    charge=-1 mult=1 basis=6-31+G(d) optimize=yes

Command line options override these.

Examples:
    python esp.py molecules/water.xyz
    python esp.py molecules/acetate.xyz --outdir results/acetate
    python esp.py molecules/ethanol.xyz --method b3lyp --basis 6-31G(d) --threads 8
"""
import argparse
import os
import sys


def read_xyz(path):
    with open(path) as f:
        lines = f.read().splitlines()
    n = int(lines[0].split()[0])
    meta = {}
    for tok in lines[1].split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            meta[k.strip().lower()] = v.strip()
    atoms = []
    for line in lines[2:2 + n]:
        sym, x, y, z = line.split()[:4]
        atoms.append((sym, float(x), float(y), float(z)))
    if len(atoms) != n:
        sys.exit(f"{path}: expected {n} atoms, found {len(atoms)}")
    return atoms, meta


def yes(value):
    return str(value).lower() in ("1", "yes", "true", "on")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xyz", help="geometry in Å (.xyz); line 2 may hold charge=, mult=, basis=, optimize=")
    ap.add_argument("--outdir", help="output folder (default: results/<xyz name>)")
    ap.add_argument("--charge", type=int, help="total charge (default: from xyz, else 0)")
    ap.add_argument("--mult", type=int, help="spin multiplicity (default: from xyz, else 1)")
    ap.add_argument("--method", default="b3lyp", help="default: b3lyp")
    ap.add_argument("--basis", help="default: from xyz, else 6-31G(d)")
    opt = ap.add_mutually_exclusive_group()
    opt.add_argument("--optimize", dest="optimize", action="store_true", default=None, help="optimize the geometry first")
    opt.add_argument("--no-optimize", dest="optimize", action="store_false", help="use the geometry as given")
    ap.add_argument("--spacing", type=float, default=0.2, help="cube grid spacing in bohr (default: 0.2)")
    ap.add_argument("--overage", type=float, default=4.0, help="cube margin around the atoms in bohr (default: 4.0)")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--memory", default="2 GB")
    a = ap.parse_args()

    atoms, meta = read_xyz(a.xyz)
    name = os.path.splitext(os.path.basename(a.xyz))[0]
    outdir = os.path.abspath(a.outdir or os.path.join("results", name))
    charge = a.charge if a.charge is not None else int(meta.get("charge", 0))
    mult = a.mult if a.mult is not None else int(meta.get("mult", 1))
    basis = a.basis or meta.get("basis", "6-31G(d)")
    optimize = a.optimize if a.optimize is not None else yes(meta.get("optimize", "yes"))
    os.makedirs(outdir, exist_ok=True)
    os.chdir(outdir)  # Psi4 writes timer.dat etc. into the working directory

    import psi4  # imported late so --help works without Psi4

    psi4.set_memory(a.memory)
    psi4.set_num_threads(a.threads)
    psi4.set_output_file(os.path.join(outdir, name + ".out"), False)
    psi4.core.IOManager.shared_object().set_default_path(outdir)

    geom = f"{charge} {mult}\n" + "\n".join(f"{s} {x:.6f} {y:.6f} {z:.6f}" for s, x, y, z in atoms)
    mol = psi4.geometry(geom, name=name)

    psi4.set_options({
        "basis": basis,
        "cubeprop_tasks": ["esp"],  # writes Dt.cube and ESP.cube
        "cubeprop_filepath": outdir,
        "cubic_grid_spacing": [a.spacing] * 3,
        "cubic_grid_overage": [a.overage] * 3,
    })
    if mult != 1:
        psi4.set_options({"reference": "uks" if a.method.lower() != "hf" else "uhf"})

    run = psi4.optimize if optimize else psi4.energy
    energy, wfn = run(a.method, molecule=mol, return_wfn=True)
    psi4.cubeprop(wfn)

    mol.update_geometry()
    with open(os.path.join(outdir, name + "_final.xyz"), "w") as f:
        f.write(mol.save_string_xyz_file())

    print(f"{name}: {a.method}/{basis}, charge {charge}, mult {mult}, "
          f"{'optimized' if optimize else 'single point'}, E = {energy:.8f} Eh")
    print(f"written to {outdir}: Dt.cube, ESP.cube, {name}.out, {name}_final.xyz")


if __name__ == "__main__":
    main()
