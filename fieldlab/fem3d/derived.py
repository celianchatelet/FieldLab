import numpy as np


def gradient_elements(champ) -> np.ndarray:
    interp = champ.basis.interpolate(champ.V)
    return interp.grad[:, :, 0].T


def centres_elements(champ) -> np.ndarray:
    return champ.mesh.p[:, champ.mesh.t].mean(axis=1).T


def champ_derive(champ, kappa_pondere: bool = False):
    grad = gradient_elements(champ)
    vecteurs = -grad
    if kappa_pondere:


        kappa_elem = champ.kappa[champ.mesh.t].mean(axis=0)
        vecteurs = vecteurs * kappa_elem[:, None]
    centres = centres_elements(champ)
    magnitude = np.linalg.norm(vecteurs, axis=1)
    return centres, vecteurs, magnitude
