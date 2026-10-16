"""Ice Ih block (usage: python make_ice.py NX NY NZ [SEED] > ice.json)

Ice Ih block with proton order obeying the ice rules (each O donates 2, accepts 2 H-bonds).

O lattice: hexagonal ice, orthorhombic cell a × √3a × c with 8 molecules.
Protons: Euler circuit through the 4-regular H-bond network (periodic), edges oriented
along the circuit → every O has 2 outgoing (its own H) and 2 incoming bonds.
"""
import json, sys
import numpy as np

a, c = 4.497, 7.322            # Å (ice Ih near 0 °C)
b = np.sqrt(3) * a
# fractional coordinates of the 8 O in the orthorhombic cell (hexagonal ice, wurtzite-like, u = 0.0625)
u = 1 / 16
# explicit: hexagonal cell O at (1/3,2/3,u),(1/3,2/3,1/2-u),(2/3,1/3,1/2+u),(2/3,1/3,1-u); convert to orthorhombic (two hexagonal cells)
hexO = [(1 / 3, 2 / 3, u), (1 / 3, 2 / 3, 0.5 - u), (2 / 3, 1 / 3, 0.5 + u), (2 / 3, 1 / 3, 1 - u)]
A1 = np.array([a, 0, 0]); A2 = np.array([-a / 2, b / 2, 0]); A3 = np.array([0, 0, c])
cart = []
for shift in [np.zeros(3), A1 + A2]:       # orthorhombic cell = hexagonal cell + its copy shifted by A1+A2
    for f in hexO:
        r = f[0] * A1 + f[1] * A2 + f[2] * A3 + shift
        cart.append(r)
cell = np.array([a, b, c])
cart = np.array([np.mod(r, cell) for r in cart])

nx, ny, nz = [int(v) for v in sys.argv[1:4]] if len(sys.argv) > 3 else (3, 2, 2)
L = cell * [nx, ny, nz]
O = np.array([cart[k] + cell * [i, j, l] for i in range(nx) for j in range(ny) for l in range(nz) for k in range(8)])
N = len(O)

def mic(d):
    return d - L * np.round(d / L)

# H-bond network: neighbours at 2.76 Å
nbr = [[] for _ in range(N)]
for i in range(N):
    for j in range(i + 1, N):
        if np.linalg.norm(mic(O[j] - O[i])) < 3.0:
            nbr[i].append(j); nbr[j].append(i)
deg = [len(n) for n in nbr]
assert all(d == 4 for d in deg), f"degrees {sorted(set(deg))}"

# Euler circuit (Hierholzer) on the multigraph, orient edges along it
rng = np.random.default_rng(int(sys.argv[4]) if len(sys.argv) > 4 else 1)
adj = {i: list(rng.permutation(nbr[i])) for i in range(N)}
used = set()
stack, circuit = [0], []
while stack:
    v = stack[-1]
    while adj[v] and frozenset((v, adj[v][-1])) in used:
        adj[v].pop()
    if adj[v]:
        w = adj[v].pop(); used.add(frozenset((v, w))); stack.append(w)
    else:
        circuit.append(stack.pop())
circuit = circuit[::-1]
donor = {}                                  # edge -> donor O
for v, w in zip(circuit, circuit[1:]):
    donor[frozenset((v, w))] = v
assert len(donor) == 2 * N
out = [sum(1 for e, d in donor.items() if d == i) for i in range(N)]
assert all(o == 2 for o in out), "ice rules violated"

# H positions: 0.9572 Å from O along O···O
H = []
for e, d in donor.items():
    v, w = tuple(e); acc = w if d == v else v
    vec = mic(O[acc] - O[d]); H.append((d, O[d] + 0.9572 * vec / np.linalg.norm(vec)))
mol = {i: [] for i in range(N)}
for d, pos in H:
    mol[d].append(pos)
atoms = []
for i in range(N):
    atoms.append({"O": O[i].round(3).tolist(), "H": [p.round(3).tolist() for p in mol[i]]})
bonds = [[int(min(tuple(e))), int(max(tuple(e)))] for e in donor]   # all H-bonds (periodic partners too)
dens = N * 18.015 / 6.02214076e23 / (np.prod(L) * 1e-24)
print(f"{N} molecules, box {L.round(2)} Å, density {dens:.3f} g/cm³, every O: 2 own H, 4 H-bonds", file=sys.stderr)
json.dump({"box": L.round(3).tolist(), "molecules": atoms, "hbonds": bonds}, sys.stdout)
