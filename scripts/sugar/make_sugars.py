#!/usr/bin/env python3
"""3D structures of the sugars for zucker.html (RDKit), with a check of every stereocentre.

The SMILES are the usual ones (PubChem). The ring atoms are numbered as in the IUPAC name
(oxane/oxolane: ring O = 1) and the CIP labels (R/S) are compared with the official names.
L-forms are not stored: the page mirrors the D-form.
Usage (rdkit env): python make_sugars.py > sugars.json
"""
import json, sys
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem import rdCIPLabeler

MOLS = {
    # key: (SMILES, {ring: expected labels by IUPAC locant}, name)
    "beta_glc": ("C([C@@H]1[C@H]([C@@H]([C@H]([C@@H](O1)O)O)O)O)O", "β-D-Glucopyranose", [("oxane", "anomeric_OH", {2: "R", 3: "R", 4: "S", 5: "S", 6: "R"})]),
    "alpha_glc": ("C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O)O)O)O)O", "α-D-Glucopyranose", [("oxane", "anomeric_OH", {2: "S", 3: "R", 4: "S", 5: "S", 6: "R"})]),
    "beta_fru": ("C1[C@H]([C@H]([C@@H]([C@](O1)(CO)O)O)O)O", "β-D-Fructopyranose", [("oxane", "anomeric_C", {2: "R", 3: "S", 4: "R", 5: "R"})]),
    "sucrose": ("C([C@@H]1[C@H]([C@@H]([C@H]([C@H](O1)O[C@]2([C@H]([C@@H]([C@H](O2)CO)O)O)CO)O)O)O)O", "Saccharose",
                [("oxane", "anomeric_glycoside", {2: "R", 3: "R", 4: "S", 5: "S", 6: "R"}), ("oxolane", "anomeric_C", {2: "S", 3: "S", 4: "S", 5: "R"})]),
    "water": ("O", "Wasser", []),
}

def ring_numbering(mol, size, kind):
    """IUPAC locants of a ring (O = 1, C2 = anomeric carbon, then away from O)."""
    ri = mol.GetRingInfo()
    for ring in ri.AtomRings():
        if len(ring) != size: continue
        o = [a for a in ring if mol.GetAtomWithIdx(a).GetSymbol() == "O"]
        if len(o) != 1: continue
        o = o[0]
        cs = [n.GetIdx() for n in mol.GetAtomWithIdx(o).GetNeighbors() if n.GetIdx() in ring]
        def exo(a): return [n for n in mol.GetAtomWithIdx(a).GetNeighbors() if n.GetIdx() not in ring and n.GetSymbol() != "H"]
        # anomeric C: carries two oxygens (ring O + exocyclic O)
        anomeric = [c for c in cs if any(n.GetSymbol() == "O" for n in exo(c))]
        if kind == "anomeric_C":    # fructose: anomeric C also carries CH2OH
            anomeric = [c for c in cs if any(n.GetSymbol() == "O" for n in exo(c)) and any(n.GetSymbol() == "C" for n in exo(c))]
        assert len(anomeric) == 1, (kind, anomeric)
        order, prev, cur = {1: o, 2: anomeric[0]}, o, anomeric[0]
        for loc in range(3, size + 1):
            nxt = [n.GetIdx() for n in mol.GetAtomWithIdx(cur).GetNeighbors() if n.GetIdx() in ring and n.GetIdx() != prev][0]
            order[loc], prev, cur = nxt, cur, nxt
        return order
    raise ValueError("ring not found")

out, ok = {}, True
for key, (smi, name, checks) in MOLS.items():
    mol = Chem.MolFromSmiles(smi); rdCIPLabeler.AssignCIPLabels(mol)
    for ring, kind, expect in checks:
        num = ring_numbering(mol, 6 if ring == "oxane" else 5, kind)
        got = {loc: (mol.GetAtomWithIdx(num[loc]).GetProp("_CIPCode") if mol.GetAtomWithIdx(num[loc]).HasProp("_CIPCode") else "-") for loc in expect}
        good = got == expect; ok &= good
        print(f"{name:20s} {ring:8s} expected {expect} got {got} {'OK' if good else 'MISMATCH'}", file=sys.stderr)
    mh = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mh, randomSeed=7); AllChem.MMFFOptimizeMolecule(mh, maxIters=2000)
    conf = mh.GetConformer(); pos = conf.GetPositions(); c = pos.mean(0)
    atoms = [[a.GetSymbol(), *[round(float(v), 3) for v in pos[a.GetIdx()] - c]] for a in mh.GetAtoms()]
    bonds = [[b.GetBeginAtomIdx(), b.GetEndAtomIdx()] for b in mh.GetBonds()]
    out[key] = {"name": name, "atoms": atoms, "bonds": bonds}
if not ok: sys.exit("stereo check failed")
json.dump(out, sys.stdout, separators=(",", ":"))
