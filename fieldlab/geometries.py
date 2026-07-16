import numpy as np

from fieldlab.grid import Field
from fieldlab import obstacles as ob

NOM_SCENE_LIBRE_2D = "Scène libre (environnement personnalisé)"


def _vides(N):
    return (np.zeros((N, N)), np.zeros((N, N), bool), np.zeros((N, N), bool))


def scene_libre(N, v):
    return _vides(N)


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


def condensateur_dielectrique_partiel(N, v):
    """Condensateur dont la moitié basse contient du verre (εr ≈ 7)."""

    V, f, s = condensateur_plan(N, v)
    source = np.zeros_like(V)
    kappa = np.full_like(V, np.nan)
    # La lame occupe une partie de l'entrefer afin de montrer la réfraction
    # des lignes à l'interface air/verre.
    kappa[int(0.20 * N):int(0.52 * N),
          int(0.25 * N):int(0.76 * N)] = 7.0
    return V, f, s, source, kappa


GEOMETRIES = {
    NOM_SCENE_LIBRE_2D: scene_libre,
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
    "Condensateur avec diélectrique partiel": condensateur_dielectrique_partiel,
}

NOMS = list(GEOMETRIES)


def build(scenarios, nom, N=120, val=10.0, walls=None, obstacles=None, q=None,
          kappa_fond=1.0, taille_domaine=1.0, rho_cp_fond=1.0,
          facteur_source=1.0):
    if nom not in scenarios:
        raise KeyError(f"Scenario inconnu : {nom!r}")
    if N < 2:
        raise ValueError(f"La resolution N doit etre au moins 2 (recu {N!r}).")

    fn = scenarios[nom]
    if q is not None:
        try:
            out = fn(N, val, q=q)
        except TypeError:
            out = fn(N, val)
    else:
        out = fn(N, val)

    kappa_scenario = rho_cp_scenario = initial_mask = None
    if len(out) >= 4:
        V, fixed, solid, source = out[:4]
        if len(out) >= 5:
            kappa_scenario = out[4]
        if len(out) >= 6:
            rho_cp_scenario = out[5]
        if len(out) >= 7:
            initial_mask = out[6]
    else:
        V, fixed, solid = out
        source = np.zeros_like(V)

    kappa = np.full_like(V, float(kappa_fond))
    rho_cp = np.full_like(V, float(rho_cp_fond))
    if kappa_scenario is not None:
        masque = np.isfinite(kappa_scenario)
        kappa[masque] = np.asarray(kappa_scenario)[masque]
    if rho_cp_scenario is not None:
        masque = np.isfinite(rho_cp_scenario)
        rho_cp[masque] = np.asarray(rho_cp_scenario)[masque]
    ob.appliquer_obstacles(V, fixed, solid, source, obstacles, kappa=kappa,
                           rho_cp=rho_cp)







    walls = walls or {c: ("neumann",) for c in ("haut", "bas", "gauche", "droite")}
    for cote, spec in walls.items():
        if spec[0] == "dirichlet":
            if cote == "haut":   V[-1, :] = spec[1]; fixed[-1, :] = True
            if cote == "bas":    V[0, :] = spec[1];  fixed[0, :] = True
            if cote == "gauche": V[:, 0] = spec[1];  fixed[:, 0] = True
            if cote == "droite": V[:, -1] = spec[1]; fixed[:, -1] = True








    h = float(taille_domaine) / (N - 1)
    return Field(V, fixed, solid, h=h, walls=walls, source=source, kappa=kappa,
                 taille_domaine=float(taille_domaine), rho_cp=rho_cp,
                 facteur_source=facteur_source,
                 initial_mask=initial_mask)


def walls_defaut(nom, val):
    return {c: ("neumann",) for c in ("haut", "bas", "gauche", "droite")}
