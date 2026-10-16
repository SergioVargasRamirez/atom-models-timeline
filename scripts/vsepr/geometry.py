"""Geometry of CH4, NH3, H2O as a function of the angle between the lower H atoms (Å).

XH3 (C3v): three H at mutual angle a below the central atom; CH4 has a fourth H on the axis
above, NH3 has its lone pair there. H2O (C2v): two H at angle a below the O atom.
"""
import numpy as np

CENTRAL = {"CH4": "C", "NH3": "N", "H2O": "O"}


def atoms(name, a, r):
    if name == "H2O":
        h = np.radians(a / 2)
        return [("O", 0.0, 0.0, 0.0), ("H", r * np.sin(h), 0.0, -r * np.cos(h)), ("H", -r * np.sin(h), 0.0, -r * np.cos(h))]
    s2 = (1 - np.cos(np.radians(a))) / 1.5          # cos a = 1 - 1.5 sin²φ
    phi = np.arcsin(np.sqrt(min(1.0, s2)))
    pos = [(CENTRAL[name], 0.0, 0.0, 0.0)]
    pos += [("H", r * np.sin(phi) * np.cos(2 * np.pi * k / 3), r * np.sin(phi) * np.sin(2 * np.pi * k / 3), -r * np.cos(phi)) for k in range(3)]
    if name == "CH4":
        pos.append(("H", 0.0, 0.0, r))
    return pos


def psi4_string(name, a, r):
    return "0 1\n" + "\n".join(f"{e} {x:.6f} {y:.6f} {z:.6f}" for e, x, y, z in atoms(name, a, r)) + "\nsymmetry c1\nno_com\nno_reorient\n"
