# Calculation scripts

Quantum chemistry (Psi4) and molecular dynamics (OpenMM) for lesson material:
electron clouds and electrostatic potentials, dipole-dipole attraction, proton
transfer. Not part of the web pages; the results are rendered with VMD or
converted for the pages.

Results go to `results/` in the folder you run from (ignored by git, the cube
files are several MB each). Every script has `--help`.

## Environments

```
conda activate psi4     # esp/, proton_transfer/  (Psi4 1.10)
conda activate openmm   # dipole_interactions/    (OpenMM 8.4)
```

## esp/ — electron density and electrostatic potential

`esp.py` computes one molecule from an `.xyz` file and writes `Dt.cube`
(density) and `ESP.cube` (potential). The comment line of the `.xyz` sets
charge, multiplicity, basis and whether to optimize; command line options
override it.

| Molecule file | Settings | Note |
|---|---|---|
| `water.xyz` | single point | experimental geometry (0.957 Å, 104.5°) |
| `hydrogen.xyz`, `chlorine.xyz`, `hydrochloric_acid.xyz` | optimized | |
| `acetic_acid.xyz` | optimized | rough start geometry, the optimizer fixes it |
| `acetate.xyz` | charge −1, 6-31+G(d), optimized | diffuse functions for the anion |
| `ethanol.xyz` | optimized | new start geometry (anti conformer) |
| `ammonia.xyz`, `carbon_dioxide.xyz`, `methane.xyz`, `nitrogen.xyz` | optimized | for elektronenwolken.html |
| `oxygen.xyz` | multiplicity 3, optimized | O₂ is a triplet (two unpaired electrons) |

Default method: B3LYP/6-31G(d).

```
cd scripts/esp
python esp.py molecules/water.xyz                      # -> results/water/
for m in molecules/*.xyz; do python esp.py $m; done    # all molecules
python butane_point_charge.py                          # butane next to +0.5 e
python butane_point_charge.py --pair --charge 1.5      # two butanes, +1.5 e
```

`butane_point_charge.py` places a point charge (an ion) next to butane and
shows the induced dipole. It refuses positions closer than 2.5 Å to an atom
(`--min-dist`), because a charge inside the electron cloud gives meaningless
results.

### Comparable colours

For pictures that can be compared between molecules, use the same density
isovalue for all surfaces (0.002 e/bohr³ is common) and the same ESP colour
range:

```
python describe_esp.py results/*/ --iso 0.002          # ESP on the surface, common range
python clip_esp.py results/*/ --common --iso 0.002     # writes ESP_clipped.cube
```

`--iso` takes the range from the ESP values on the surface. Without it, the
percentiles of the whole grid are dominated by the large values near the nuclei.

### Data for the page elektronenwolken.html

```
cd scripts/esp
for m in water hydrogen chlorine hydrochloric_acid ammonia carbon_dioxide \
         methane nitrogen oxygen; do python esp.py molecules/$m.xyz --overage 5; done
python export_web.py          # -> template/site/wolken-data.js
cd ../.. && python3 build.py  # copies the data into elektronenwolken.html
```

`export_web.py` resamples the grids to 0.3 bohr, stores the density as
log-scaled bytes and the ESP on one shared range (from the surface at 0.002),
and adds the share of electrons inside the surface for a range of isovalues.

## dipole_interactions/ — clusters with OpenMM

| Script | What it shows |
|---|---|
| `h2.py` | H₂ without charges: almost no attraction, stays disordered |
| `hcl.py` | HCl with partial charges: molecules line up H···Cl |
| `h2o.py` | water (TIP3P): hydrogen-bonded cluster |

`hcl.py` uses ±0.4 e **on purpose**: twice the real dipole, so the alignment is
clearly visible. `--charge 0.18` gives the measured 1.08 D.

```
cd scripts/dipole_interactions
python hcl.py --seed 1                  # -> results/hcl/: hcl_initial.pdb, hcl.dcd, hcl_final.pdb, hcl.csv
vmd results/hcl/hcl_initial.pdb results/hcl/hcl.dcd
```

## proton_transfer/ — acetic acid gives a proton to water

`proton_trajectory.py` moves the acidic proton along the O···O hydrogen bond
from acetic acid to water (H₃O⁺) and writes snapshots plus a multi-frame
`trajectory.xyz`. `--energies` adds a Psi4 energy for every step. In the gas
phase with one water molecule the transfer is strongly uphill (≈ +200 kJ/mol);
only the surrounding water in solution makes it run.

```
cd scripts/proton_transfer
python proton_trajectory.py --steps 30
python proton_trajectory.py --energies
```
