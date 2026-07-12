import numpy as np


def champ_electrique(field):
    dVdy, dVdx = np.gradient(field.V, field.h)
    Ex = -dVdx
    Ey = -dVdy
    Ex[field.solid_mask] = 0.0
    Ey[field.solid_mask] = 0.0
    return Ex, Ey, np.hypot(Ex, Ey)


def champ_magnetique(field):
    dAdy, dAdx = np.gradient(field.V, field.h)
    Bx = dAdy
    By = -dAdx
    Bx[field.solid_mask] = 0.0
    By[field.solid_mask] = 0.0
    return Bx, By, np.hypot(Bx, By)


def flux_thermique(field, k=None):
    if k is None:
        k = field.kappa
    dTdy, dTdx = np.gradient(field.V, field.h)
    phix = -k * dTdx
    phiy = -k * dTdy
    phix[field.solid_mask] = 0.0
    phiy[field.solid_mask] = 0.0
    return phix, phiy, np.hypot(phix, phiy)
