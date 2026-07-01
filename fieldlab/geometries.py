import numpy as np

from fieldlab.grid import Field
from fieldlab import obstacles as ob


def _vides(N):
    return (np.zeros((N, N)), np.zeros((N, N), bool), np.zeros((N, N), bool))


def condensateur_plan(N, v):
    V, f, s = _vides(N)
    ob.segment_v(V, f, s, 0.25, 0.20, 0.80, ("dirichlet", v))
    ob.segment_v(V, f, s, 0.75, 0.20, 0.80, ("dirichlet", 0.0))
    return V, f, s


def condensateur_obstacle_isolant(N, v):
    V, f, s = condensateur_plan(N, v)
    ob.disque(V, f, s, 0.50, 0.50, 0.12, ("isolant",))
    return V, f, s


def condensateur_obstacle_conducteur(N, v):
    V, f, s = condensateur_plan(N, v)
    ob.disque(V, f, s, 0.50, 0.50, 0.12, ("dirichlet", v / 2))
    return V, f, s


def dipole(N, v):
    V, f, s = _vides(N)
    ob.disque(V, f, s, 0.32, 0.50, 0.07, ("dirichlet", v))
    ob.disque(V, f, s, 0.68, 0.50, 0.07, ("dirichlet", 0.0))
    return V, f, s


def quadripole(N, v):
    V, f, s = _vides(N)
    ob.disque(V, f, s, 0.32, 0.32, 0.06, ("dirichlet", v))
    ob.disque(V, f, s, 0.68, 0.32, 0.06, ("dirichlet", 0.0))
    ob.disque(V, f, s, 0.32, 0.68, 0.06, ("dirichlet", 0.0))
    ob.disque(V, f, s, 0.68, 0.68, 0.06, ("dirichlet", v))
    return V, f, s


def cable_coaxial(N, v):
    V, f, s = _vides(N)
    ob.anneau(V, f, s, 0.50, 0.50, 0.46, 0.40, ("dirichlet", 0.0))
    ob.disque(V, f, s, 0.50, 0.50, 0.10, ("dirichlet", v))
    return V, f, s


def pointe_plan(N, v):
    V, f, s = _vides(N)
    ob.segment_v(V, f, s, 0.80, 0.10, 0.90, ("dirichlet", 0.0))
    for k in range(int(0.18 * N)):
        x = 0.20 + k / N
        demi = 0.18 * (1 - k / (0.18 * N))
        ob.segment_v(V, f, s, x, 0.50 - demi, 0.50 + demi + 1e-6, ("dirichlet", v))
    return V, f, s


def cage_faraday(N, v):
    V, f, s = _vides(N)
    ob.segment_v(V, f, s, 0.10, 0.15, 0.85, ("dirichlet", v))
    ob.segment_v(V, f, s, 0.90, 0.15, 0.85, ("dirichlet", -v))
    ob.anneau(V, f, s, 0.50, 0.50, 0.26, 0.23, ("dirichlet", 0.0))
    return V, f, s


def lentille_electrostatique(N, v):
    V, f, s = _vides(N)
    for x, val in ((0.30, 0.0), (0.50, v), (0.70, 0.0)):
        ob.segment_v(V, f, s, x, 0.10, 0.42, ("dirichlet", val), ep=2)
        ob.segment_v(V, f, s, x, 0.58, 0.90, ("dirichlet", val), ep=2)
    return V, f, s


def ligne_bifilaire(N, v):
    V, f, s = _vides(N)
    ob.disque(V, f, s, 0.38, 0.50, 0.05, ("dirichlet", v))
    ob.disque(V, f, s, 0.62, 0.50, 0.05, ("dirichlet", 0.0))
    return V, f, s


def condensateur_en_coin(N, v):
    V, f, s = _vides(N)
    ob.segment_h(V, f, s, 0.30, 0.20, 0.80, ("dirichlet", v))
    ob.segment_v(V, f, s, 0.20, 0.30, 0.80, ("dirichlet", 0.0))
    return V, f, s


def peigne(N, v):
    V, f, s = _vides(N)
    ob.segment_h(V, f, s, 0.20, 0.15, 0.85, ("dirichlet", v), ep=2)
    for k in range(5):
        x = 0.20 + k * 0.15
        ob.segment_v(V, f, s, x, 0.20, 0.55, ("dirichlet", v))
    ob.segment_h(V, f, s, 0.80, 0.15, 0.85, ("dirichlet", 0.0), ep=2)
    return V, f, s


def microruban(N, v):
    V, f, s = _vides(N)
    ob.segment_h(V, f, s, 0.85, 0.05, 0.95, ("dirichlet", 0.0), ep=2)
    ob.segment_h(V, f, s, 0.30, 0.38, 0.62, ("dirichlet", v), ep=2)
    return V, f, s


def electrodes_circulaires(N, v):
    V, f, s = _vides(N)
    ob.disque(V, f, s, 0.35, 0.50, 0.05, ("dirichlet", v))
    ob.disque(V, f, s, 0.65, 0.50, 0.05, ("dirichlet", 0.0))
    return V, f, s


GEOMETRIES = {
    "Condensateur plan": condensateur_plan,
    "Condensateur + obstacle isolant": condensateur_obstacle_isolant,
    "Condensateur + obstacle conducteur": condensateur_obstacle_conducteur,
    "Dipole (deux disques)": dipole,
    "Quadripole": quadripole,
    "Cable coaxial": cable_coaxial,
    "Pointe - plan (effet de pointe)": pointe_plan,
    "Cage de Faraday": cage_faraday,
    "Lentille electrostatique": lentille_electrostatique,
    "Ligne bifilaire": ligne_bifilaire,
    "Condensateur en coin": condensateur_en_coin,
    "Peigne interdigite": peigne,
    "Micro-ruban (microstrip)": microruban,
    "Electrodes circulaires": electrodes_circulaires,
}

NOMS = list(GEOMETRIES)


def build(scenarios, nom, N=120, val=10.0, walls=None, obstacles=None, q=None):
    """Construit un Field a partir d'un scenario.

    q : puissance volumique (thermique) ou courant additionnel (magneto) passe
    en 3e argument aux builders qui l'acceptent. Les autres l'ignorent.
    """
    if nom not in scenarios:
        raise KeyError(f"Scenario inconnu : {nom!r}")

    fn = scenarios[nom]
    if q is not None:
        try:
            out = fn(N, val, q=q)
        except TypeError:
            out = fn(N, val)
    else:
        out = fn(N, val)

    if len(out) == 4:
        V, fixed, solid, source = out
    else:                                   # builders electrostatiques (3-uplet)
        V, fixed, solid = out
        source = np.zeros_like(V)

    ob.appliquer_obstacles(V, fixed, solid, source, obstacles)

    walls = walls or {c: ("neumann",) for c in ("haut", "bas", "gauche", "droite")}
    for cote, spec in walls.items():
        if spec[0] == "dirichlet":
            if cote == "haut":   V[0, :] = spec[1];  fixed[0, :] = True
            if cote == "bas":    V[-1, :] = spec[1]; fixed[-1, :] = True
            if cote == "gauche": V[:, 0] = spec[1];  fixed[:, 0] = True
            if cote == "droite": V[:, -1] = spec[1]; fixed[:, -1] = True

    return Field(V, fixed, solid, h=1.0, walls=walls, source=source)


def walls_defaut(nom, val):
    """Electrostatique : electrodes internes, bords libres par defaut."""
    return {c: ("neumann",) for c in ("haut", "bas", "gauche", "droite")}
