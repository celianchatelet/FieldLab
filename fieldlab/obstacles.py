import numpy as np


def _appliquer(V, fixed, solid, masque, bc, source=None):
    if bc[0] == "dirichlet":
        V[masque] = bc[1]
        fixed[masque] = True
        solid[masque] = False
    elif bc[0] == "isolant":
        solid[masque] = True
        fixed[masque] = False
        V[masque] = 0.0
    elif bc[0] == "source":
        # Region source : injecte J (magneto) ou q (thermique) dans field.source
        if source is not None:
            source[masque] = bc[1]
    else:
        raise ValueError(f"Condition inconnue : {bc!r}")


def disque(V, fixed, solid, cx, cy, r, bc, source=None):
    N = V.shape[0]
    Y, X = np.ogrid[:N, :N]
    m = (X - cx * N) ** 2 + (Y - cy * N) ** 2 <= (r * N) ** 2
    _appliquer(V, fixed, solid, m, bc, source)


def anneau(V, fixed, solid, cx, cy, r_ext, r_int, bc, source=None):
    N = V.shape[0]
    Y, X = np.ogrid[:N, :N]
    d2 = (X - cx * N) ** 2 + (Y - cy * N) ** 2
    m = (d2 <= (r_ext * N) ** 2) & (d2 >= (r_int * N) ** 2)
    _appliquer(V, fixed, solid, m, bc, source)


def rectangle(V, fixed, solid, x0, y0, x1, y1, bc, source=None):
    N = V.shape[0]
    a, b = int(y0 * N), int(y1 * N)
    c, d = int(x0 * N), int(x1 * N)
    m = np.zeros(V.shape, dtype=bool)
    m[a:b, c:d] = True
    _appliquer(V, fixed, solid, m, bc, source)


def segment_v(V, fixed, solid, x, y0, y1, bc, ep=1, source=None):
    N = V.shape[0]
    a, b = int(y0 * N), int(y1 * N)
    c = int(x * N)
    m = np.zeros(V.shape, dtype=bool)
    m[a:b, c:c + ep] = True
    _appliquer(V, fixed, solid, m, bc, source)


def segment_h(V, fixed, solid, y, x0, x1, bc, ep=1, source=None):
    N = V.shape[0]
    a, b = int(x0 * N), int(x1 * N)
    r = int(y * N)
    m = np.zeros(V.shape, dtype=bool)
    m[r:r + ep, a:b] = True
    _appliquer(V, fixed, solid, m, bc, source)

FORMES = {
    "disque": disque,
    "anneau": anneau,
    "rectangle": rectangle,
    "segment_v": segment_v,
    "segment_h": segment_h,
}


def appliquer_obstacles(V, fixed, solid, source, obstacles):
    for o in obstacles or []:
        FORMES[o["forme"]](V, fixed, solid, bc=o["bc"], source=source, **o["args"])
