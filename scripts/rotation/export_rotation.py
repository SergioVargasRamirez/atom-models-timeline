#!/usr/bin/env python3
"""Export the torsion scans for drehung.html → template/site/drehung-data.js.

Run scan_torsion.py for ethane, ethene and ethyne first (see scripts/README.md), then
    python export_rotation.py
`python3 build.py` copies the data into the page.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "template", "site", "drehung-data.js")
MOLS = [("ethane", "1,2-Dichlorethan", "ClH₂C–CH₂Cl", 1),
        ("ethene", "1,2-Dichlorethen", "ClHC=CHCl", 2),
        ("ethyne", "1,2-Dichlorethin", "ClC≡CCl", 3)]

data = []
for key, name, formula, order in MOLS:
    scan = json.load(open(os.path.join(HERE, "results", f"{key}.json")))
    pts = scan["points"]
    if pts[0]["phi"] is not None:
        phis = [p["phi"] for p in pts]
        assert phis == sorted(phis) and phis[0] == 0 and phis[-1] == 180, f"{key}: Scan muss 0° bis 180° abdecken"
        assert len({len(p["atoms"]) for p in pts}) == 1, f"{key}: Atomzahl wechselt"
    data.append({"key": key, "name": name, "formula": formula, "order": order, "method": scan["method"],
                 "phi": [p["phi"] for p in pts], "dE": [round(p["dE"], 2) for p in pts], "mu": [p["mu"] for p in pts],
                 "atoms": [p["atoms"] for p in pts]})
    if pts[0]["phi"] is not None:
        i = max(range(len(pts)), key=lambda k: pts[k]["dE"])
        print(f"{name}: Hürde {pts[i]['dE']:.1f} kJ/mol bei {pts[i]['phi']:.0f}°, "
              f"0° {pts[0]['dE']:.1f} kJ/mol ({pts[0]['mu']:.2f} D), 180° {pts[-1]['dE']:.1f} kJ/mol ({pts[-1]['mu']:.2f} D)")

js = ("/* Erzeugt von scripts/rotation/export_rotation.py (Psi4: B3LYP/def2-TZVP, Diederwinkel Cl–C–C–Cl eingefroren). "
      "Nicht von Hand bearbeiten. */\nconst DREHUNG = " + json.dumps({"molecules": data}, ensure_ascii=False, separators=(",", ":")) + ";\n")
open(OUT, "w", encoding="utf-8").write(js)
print(f"{os.path.relpath(OUT, HERE)}: {len(js) / 1024:.0f} KB")
