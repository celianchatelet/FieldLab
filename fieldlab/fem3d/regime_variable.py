from time import perf_counter

import numpy as np

from fieldlab.annulation import verifier
from fieldlab.fem3d.field3d import Field3D
from fieldlab.fem3d.poisson import (
    FactorisationDirichlet, METHODES_FEM3D, preparer_systeme_3d, resoudre_systeme_3d,
)
from fieldlab.fem3d.transient import TransientResult3D
from fieldlab.sources import FORMES_TEMPORELLES


def resoudre_regime_variable_3d(champ0: Field3D, noeuds_amplitude: np.ndarray,
                                 valeur_pic: float, forme: str, frequence: float,
                                 duree: float, n_images: int = 60,
                                 methode: str = "direct", progress=None,
                                 annule=None) -> TransientResult3D:
    if forme not in FORMES_TEMPORELLES:
        raise KeyError(f"Forme temporelle inconnue : {forme!r}. Choix : {list(FORMES_TEMPORELLES)}")
    if methode not in METHODES_FEM3D:
        raise KeyError(f"Methode FEM 3D inconnue : {methode!r}. Choix : {METHODES_FEM3D}")
    if duree <= 0:
        raise ValueError("La duree simulee doit etre strictement positive.")

    forme_fn = FORMES_TEMPORELLES[forme]
    instants = np.linspace(0.0, duree, max(2, n_images + 1))

    systeme = preparer_systeme_3d(champ0)
    D = np.nonzero(champ0.fixed_mask)[0]
    cache = FactorisationDirichlet(systeme, D) if methode == "direct" else None

    champs = []
    convergence_globale = True
    t0 = perf_counter()
    for k, t in enumerate(instants):
        verifier(annule)
        val = float(forme_fn(t, valeur_pic, frequence))
        champ_t = champ0.copy()
        champ_t.V[noeuds_amplitude] = val
        res = resoudre_systeme_3d(
            systeme, champ_t, methode=methode, cache=cache, annule=annule)
        champs.append(res.champ)
        convergence_globale = convergence_globale and bool(res.converge)
        if progress is not None:
            progress(k + 1, 0.0)

    temps_calcul = perf_counter() - t0
    dt = float(instants[1] - instants[0]) if len(instants) > 1 else duree
    return TransientResult3D(champs, list(instants), dt, temps_calcul,
                              convergence_globale, len(champs))
