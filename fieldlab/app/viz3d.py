import numpy as np
import pyvista as pv




_EXAGERATION_Z = 0.35

_LONGUEUR_MAX_GLYPHE = 0.12



_PAS_GLYPHES = 6


def _taille(field) -> float:
    return float(getattr(field, "taille_domaine", 1.0) or 1.0)


def _grille_elevation(valeurs_z: np.ndarray, valeurs_couleur: np.ndarray,
                       nom_scalaire: str, taille: float) -> pv.StructuredGrid:
    ny, nx = valeurs_z.shape
    x = np.linspace(0.0, taille, nx)
    y = np.linspace(0.0, taille, ny)
    X, Y = np.meshgrid(x, y)
    etendue = valeurs_z.max() - valeurs_z.min()
    Z = (_EXAGERATION_Z * taille * (valeurs_z - valeurs_z.min()) / etendue
         if etendue > 1e-12 else np.zeros_like(valeurs_z))
    grille = pv.StructuredGrid(X, Y, Z)
    grille[nom_scalaire] = valeurs_couleur.ravel(order="F")
    return grille


def construire_surface(field, scalaire: str) -> pv.StructuredGrid:
    return _grille_elevation(field.V, field.V, scalaire, _taille(field))


def construire_intensite(field, champ_fn, champ: str):
    _, _, mag = champ_fn(field)
    return _grille_elevation(mag, mag, f"|{champ}|", _taille(field))


def construire_vecteurs(field, champ_fn, champ: str, pas: int = _PAS_GLYPHES) -> pv.PolyData:
    Fx, Fy, mag = champ_fn(field)
    ny, nx = field.V.shape
    taille = _taille(field)
    x = np.linspace(0.0, taille, nx)
    y = np.linspace(0.0, taille, ny)
    X, Y = np.meshgrid(x, y)
    s = slice(None, None, pas)
    Xs, Ys, Fxs, Fys, mags = X[s, s], Y[s, s], Fx[s, s], Fy[s, s], mag[s, s]

    n = Xs.size
    points = np.column_stack([Xs.ravel(), Ys.ravel(), np.zeros(n)])
    vecteurs = np.column_stack([Fxs.ravel(), Fys.ravel(), np.zeros(n)])
    nuage = pv.PolyData(points)
    nuage["vecteurs"] = vecteurs
    nuage["intensite"] = mags.ravel()
    return nuage


def construire_lignes(field, champ_fn) -> pv.PolyData:
    Fx, Fy, mag = champ_fn(field)
    ny, nx = field.V.shape
    taille = _taille(field)
    epaisseur = 0.01 * taille
    grille = pv.ImageData(
        dimensions=(nx, ny, 2),
        spacing=(taille / max(nx - 1, 1), taille / max(ny - 1, 1), epaisseur),
        origin=(0.0, 0.0, 0.0))


    plan = np.column_stack([
        Fx.ravel(), Fy.ravel(), np.zeros(Fx.size)])
    grille["champ2d"] = np.vstack([plan, plan])
    grille["intensite"] = np.concatenate([mag.ravel(), mag.ravel()])

    germes_1d = np.linspace(0.08 * taille, 0.92 * taille, 10)
    gx, gy = np.meshgrid(germes_1d, germes_1d)
    germes = pv.PolyData(np.column_stack([
        gx.ravel(), gy.ravel(), np.full(gx.size, epaisseur / 2.0)]))
    kwargs = {
        "vectors": "champ2d", "integration_direction": "both",
        "initial_step_length": 0.25, "max_steps": 2000,
        "compute_vorticity": False,
    }
    try:
        return grille.streamlines_from_source(
            germes, max_length=4.0 * taille, **kwargs)
    except TypeError:

        return grille.streamlines_from_source(
            germes, max_time=4.0 * taille, **kwargs)


def _ajouter_fleches(plotter, field, champ_fn, champ: str) -> None:
    nuage = construire_vecteurs(field, champ_fn, champ)
    mmax = float(nuage["intensite"].max())
    facteur = (_LONGUEUR_MAX_GLYPHE * _taille(field) / mmax
               if mmax > 1e-12 else 0.0)
    fleches = nuage.glyph(orient="vecteurs", scale="intensite",
                           factor=facteur, geom=pv.Arrow())
    plotter.add_mesh(fleches, scalars="intensite", cmap="RdBu_r",
                      scalar_bar_args={"title": f"|{champ}|"})


def dessiner(plotter, field, kind: str, champ_fn, scalaire: str, champ: str,
             theme_sombre: bool = False) -> None:
    plotter.clear()

    if kind == "Iso-valeurs":
        grille = construire_surface(field, scalaire)
        contours = grille.contour(isosurfaces=12, scalars=scalaire)
        plotter.add_mesh(grille, scalars=scalaire, cmap="plasma", opacity=0.55,
                          smooth_shading=True)
        if contours.n_points > 0:
            plotter.add_mesh(contours, color="black", line_width=2)

    elif kind == "Champ (flèches)":
        fond = construire_surface(field, scalaire)
        plotter.add_mesh(fond, scalars=scalaire, cmap="plasma", opacity=0.35,
                          smooth_shading=True, show_scalar_bar=False)
        _ajouter_fleches(plotter, field, champ_fn, champ)

    elif kind == "Lignes de champ":
        fond = construire_surface(field, scalaire)
        plotter.add_mesh(fond, scalars=scalaire, cmap="plasma", opacity=0.35,
                          smooth_shading=True, show_scalar_bar=False)
        try:
            lignes = construire_lignes(field, champ_fn)
            if lignes.n_points == 0:
                raise ValueError("aucune ligne integree")
            tubes = lignes.tube(
                radius=0.003 * _taille(field), n_sides=8)
            plotter.add_mesh(tubes, scalars="intensite", cmap="RdBu_r",
                              scalar_bar_args={"title": f"|{champ}|"})
        except (KeyError, RuntimeError, TypeError, ValueError):
            _ajouter_fleches(plotter, field, champ_fn, champ)

    elif kind == "Intensité du champ":
        grille = construire_intensite(field, champ_fn, champ)
        plotter.add_mesh(grille, scalars=f"|{champ}|", cmap="inferno",
                          smooth_shading=True)

    else:
        grille = construire_surface(field, scalaire)
        plotter.add_mesh(grille, scalars=scalaire, cmap="plasma",
                          smooth_shading=True)

    plotter.add_axes()
    couleur_axes = "#9aa7bd" if theme_sombre else "#4b5563"
    try:
        plotter.show_grid(xtitle="x (m)", ytitle="y (m)", ztitle="",
                          color=couleur_axes)
    except TypeError:
        try:
            plotter.show_grid(xtitle="x (m)", ytitle="y (m)", ztitle="")
        except TypeError:
            plotter.show_grid()
    plotter.reset_camera()
