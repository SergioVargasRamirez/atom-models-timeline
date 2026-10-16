"""Read and write Gaussian cube files (shared by describe_esp.py and clip_esp.py)."""
import numpy as np


def read_cube(path):
    """Return (header_lines, atom_lines, values, shape). Values are flat, in file order."""
    with open(path) as f:
        header = [next(f) for _ in range(6)]
        natoms = abs(int(header[2].split()[0]))
        atoms = [next(f) for _ in range(natoms)]
        values = np.array(f.read().split(), dtype=float)
    shape = tuple(abs(int(header[i].split()[0])) for i in (3, 4, 5))
    if values.size != np.prod(shape):
        raise ValueError(f"{path}: {values.size} values, grid needs {np.prod(shape)}")
    return header, atoms, values, shape


def write_cube(path, header, atoms, values, shape):
    """Write values with the usual layout: 6 per line, new line after each z row."""
    nz = shape[2]
    with open(path, "w") as f:
        f.writelines(header)
        f.writelines(atoms)
        for row in values.reshape(-1, nz):
            for i in range(0, nz, 6):
                f.write(" ".join(f"{v:13.6e}" for v in row[i:i + 6]) + "\n")


def surface_values(esp, density, iso, tol=0.25):
    """ESP values on the density isosurface: grid points with density within ±tol·iso of iso."""
    mask = np.abs(density - iso) <= tol * iso
    return esp[mask]
