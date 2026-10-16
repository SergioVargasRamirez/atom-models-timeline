#!/usr/bin/env python3
"""Export the angle scans and localized orbitals for vsepr.html → template/site/vsepr-data.js.

Run scan.py and lmo.py for CH4, NH3, H2O first (see scripts/README.md), then
    python export_vsepr.py
`python3 build.py` copies the data into the page.
"""
import base64, glob, gzip, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "esp"))
from cube_tools import read_grid                       # noqa: E402
sys.path.insert(0, os.path.join(HERE, "..", "esp"))
from export_web import resample                         # noqa: E402

BOHR = 0.529177210903
OUT = os.path.join(HERE, "..", "..", "template", "site", "vsepr-data.js")
MOLS = [("CH4", "Methan", "CH₄", "C"), ("NH3", "Ammoniak", "NH₃", "N"), ("H2O", "Wasser", "H₂O", "O")]
STEP, CUT, SCALE = 0.3, 0.015, 0.30                     # grid spacing (bohr), crop level, int8 full scale

def pack(arr):
    return base64.b64encode(gzip.compress(arr.astype(np.int8).tobytes(order="C"), 9, mtime=0)).decode()

data, total = [], 0
for key, name, formula, central in MOLS:
    res = os.path.join(HERE, "results")
    scan = json.load(open(os.path.join(res, f"{key}_scan.json")))
    lmo = json.load(open(os.path.join(res, f"{key}_lmo", "lmo.json")))
    pairs = []
    for p in lmo["pairs"]:
        if p["kind"] == "core":
            continue
        g = read_grid(glob.glob(os.path.join(res, f"{key}_lmo", f"Psi_a_{p['index']}_*.cube"))[0])
        v = g["values"]
        v = v * np.sign(v.flat[np.argmax(np.abs(v))])   # main lobe positive
        v2 = resample(v, g["step"], STEP)
        idx = np.argwhere(np.abs(v2) >= CUT)
        lo, hi = np.maximum(idx.min(0) - 2, 0), np.minimum(idx.max(0) + 3, v2.shape)
        v2 = v2[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        q = np.clip(np.round(v2 / SCALE * 127), -127, 127)
        packed = pack(q); total += len(packed)
        pairs.append({"kind": p["kind"], "dist": p["dist"], "spread": p["spread"], "angular": p["angular"],
                      "origin": [round(float(o) * BOHR, 4) for o in g["origin"] + lo * STEP], "step": round(STEP * BOHR, 5),
                      "shape": list(v2.shape), "scale": SCALE, "data": packed})
    data.append({"key": key, "name": name, "formula": formula, "central": central, "method": scan["method"],
                 "scan": {"angle": scan["angle"], "r": scan["r"], "dE": scan["dE_kJ"]},
                 "min": {"angle": lmo["angle"], "r": lmo["r"]}, "pairs": pairs})
    print(f"{key}: minimum {lmo['angle']}°, {len(pairs)} pairs")
with open(OUT, "w") as f:
    f.write("/* Erzeugt von scripts/vsepr/export_vsepr.py (Psi4: MP2/aug-cc-pVTZ-Winkelscan, Boys-Orbitale B3LYP/cc-pVTZ). Nicht von Hand bearbeiten. */\n")
    f.write("const VSEPR = " + json.dumps({"molecules": data}, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"written {os.path.relpath(OUT)}: {total / 1024:.0f} kB orbital data")
