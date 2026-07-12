import numpy as np


def base_plan(normale):
    n = np.asarray(normale, dtype=float)
    norme = float(np.linalg.norm(n))
    if norme <= 1e-14:
        raise ValueError("La normale d'un plan ne peut pas etre nulle.")
    n = n / norme

    axe = np.zeros(3)
    axe[int(np.argmin(np.abs(n)))] = 1.0
    u = np.cross(n, axe)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return u, v


class ChampPlan2D:
    def __init__(self, Fu, Fv, valide, su, sv):
        self.Fu = np.asarray(Fu, dtype=float)
        self.Fv = np.asarray(Fv, dtype=float)
        self.valide = np.asarray(valide, dtype=bool)
        self.su = np.asarray(su, dtype=float)
        self.sv = np.asarray(sv, dtype=float)
        if self.Fu.shape != self.Fv.shape or self.Fu.shape != self.valide.shape:
            raise ValueError("Composantes et masque doivent avoir la meme forme.")
        if self.Fu.shape != (len(self.su), len(self.sv)):
            raise ValueError("La grille ne correspond pas aux abscisses.")
        self.du = float(self.su[1] - self.su[0]) if len(self.su) > 1 else 1.0
        self.dv = float(self.sv[1] - self.sv[0]) if len(self.sv) > 1 else 1.0

    def _indices(self, p):
        return ((p[0] - self.su[0]) / self.du,
                (p[1] - self.sv[0]) / self.dv)

    def dans_grille(self, p):
        i, j = self._indices(p)
        return 0.0 <= i <= len(self.su) - 1 and 0.0 <= j <= len(self.sv) - 1

    def vecteur(self, p):
        if not self.dans_grille(p):
            return None
        i, j = self._indices(p)
        i0 = min(int(i), len(self.su) - 2) if len(self.su) > 1 else 0
        j0 = min(int(j), len(self.sv) - 2) if len(self.sv) > 1 else 0
        i1, j1 = min(i0 + 1, len(self.su) - 1), min(j0 + 1, len(self.sv) - 1)
        if not (self.valide[i0, j0] and self.valide[i0, j1]
                and self.valide[i1, j0] and self.valide[i1, j1]):
            return None
        tx, ty = i - i0, j - j0
        p00 = np.array([self.Fu[i0, j0], self.Fv[i0, j0]])
        p01 = np.array([self.Fu[i0, j1], self.Fv[i0, j1]])
        p10 = np.array([self.Fu[i1, j0], self.Fv[i1, j0]])
        p11 = np.array([self.Fu[i1, j1], self.Fv[i1, j1]])
        return ((1 - tx) * (1 - ty) * p00 + (1 - tx) * ty * p01
                + tx * (1 - ty) * p10 + tx * ty * p11)


def _direction(champ, p, seuil):
    f = champ.vecteur(p)
    if f is None:
        return None
    norme = float(np.linalg.norm(f))
    if norme <= seuil:
        return None
    return f / norme


def _integrer_sens(champ, depart, pas, n_max, seuil, sens):
    points = []
    p = np.asarray(depart, dtype=float).copy()
    for _ in range(n_max):
        d1 = _direction(champ, p, seuil)
        if d1 is None:
            break
        d2 = _direction(champ, p + sens * 0.5 * pas * d1, seuil)
        if d2 is None:
            break
        d3 = _direction(champ, p + sens * 0.5 * pas * d2, seuil)
        if d3 is None:
            break
        d4 = _direction(champ, p + sens * pas * d3, seuil)
        if d4 is None:
            break
        p = p + sens * (pas / 6.0) * (d1 + 2 * d2 + 2 * d3 + d4)
        if not champ.dans_grille(p):
            break
        points.append(p.copy())
    return points


def integrer_lignes(champ: ChampPlan2D, graines, pas=None, n_max=600,
                    seuil_relatif=0.02, rayon_exclusion=1.0):
    magnitudes = np.hypot(champ.Fu, champ.Fv)[champ.valide]
    if magnitudes.size == 0:
        return []
    seuil = float(seuil_relatif) * float(np.percentile(magnitudes, 98.0)) \
        if magnitudes.size else 0.0
    if pas is None:
        pas = 0.6 * min(champ.du, champ.dv)
    occupation = np.zeros_like(champ.valide, dtype=bool)
    rayon = max(0, int(round(rayon_exclusion)))

    def _cellule(p):
        i, j = champ._indices(p)
        return (int(round(i)), int(round(j)))

    def _occupee(p):
        i, j = _cellule(p)
        if not (0 <= i < occupation.shape[0] and 0 <= j < occupation.shape[1]):
            return False
        return bool(occupation[i, j])

    def _marquer(p):
        i, j = _cellule(p)
        i0, i1 = max(0, i - rayon), min(occupation.shape[0], i + rayon + 1)
        j0, j1 = max(0, j - rayon), min(occupation.shape[1], j + rayon + 1)
        occupation[i0:i1, j0:j1] = True

    lignes = []
    for graine in graines:
        graine = np.asarray(graine, dtype=float)
        if _direction(champ, graine, seuil) is None or _occupee(graine):
            continue
        arriere = _integrer_sens(champ, graine, pas, n_max, seuil, -1.0)
        avant = _integrer_sens(champ, graine, pas, n_max, seuil, +1.0)
        points = list(reversed(arriere)) + [graine] + avant
        if len(points) < 4:
            continue
        ligne = np.asarray(points)
        for p in ligne[::2]:
            _marquer(p)
        lignes.append(ligne)
    return lignes


def graines_grille_plan(champ: ChampPlan2D, cote=7, marge=0.05):
    cote = max(2, int(cote))
    su0, su1 = champ.su[0], champ.su[-1]
    sv0, sv1 = champ.sv[0], champ.sv[-1]
    eu, ev = su1 - su0, sv1 - sv0
    graines = []
    for a in np.linspace(su0 + marge * eu, su1 - marge * eu, cote):
        for b in np.linspace(sv0 + marge * ev, sv1 - marge * ev, cote):
            graines.append((float(a), float(b)))
    return graines


def lignes_vers_3d(lignes_2d, origine, u, v):
    origine = np.asarray(origine, dtype=float)
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    return [origine + ligne[:, 0:1] * u + ligne[:, 1:2] * v
            for ligne in lignes_2d]
