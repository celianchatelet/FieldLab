import numpy as np

from fieldlab.field import champ_electrique

KINDS = [
    "Carte scalaire",
    "Iso-valeurs",
    "Champ (flèches)",
    "Lignes de champ",
    "Intensité du champ",
]


def _etendue(field):
    L = float(getattr(field, "taille_domaine", 1.0) or 1.0)
    return (0.0, L, 0.0, L)


def _grilles_metres(field):
    ny, nx = field.shape
    L = float(getattr(field, "taille_domaine", 1.0) or 1.0)
    x = np.linspace(0.0, L, nx)
    y = np.linspace(0.0, L, ny)
    return np.meshgrid(x, y)


def _axes_metres(ax):
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")


def _valeurs_sans_objets(field):
    masque = np.asarray(field.solid_mask, dtype=bool).copy()
    fixes = np.asarray(field.fixed_mask, dtype=bool).copy()
    if fixes.ndim == 2 and min(fixes.shape) > 2:
        fixes[0, :] = fixes[-1, :] = False
        fixes[:, 0] = fixes[:, -1] = False
    masque |= fixes
    return np.ma.array(field.V, mask=masque)


def _overlay_solides(ax, field):
    if field.solid_mask.any():
        gris = np.where(field.solid_mask, 1.0, np.nan)
        ax.imshow(gris, origin="lower", cmap="Greys", vmin=0, vmax=1.4,
                  alpha=0.9, extent=_etendue(field))


def _overlay_electrodes(ax, field):
    elec = field.fixed_mask.copy()
    elec[0, :] = elec[-1, :] = elec[:, 0] = elec[:, -1] = False
    if not elec.any():
        return
    m = elec.astype(float)
    ext = _etendue(field)
    ax.contour(m, levels=[0.5], colors="white", linewidths=2.6, alpha=0.9,
               extent=ext)
    ax.contour(m, levels=[0.5], colors="black", linewidths=1.3, extent=ext)


def _overlay_sources(ax, field):
    src = field.source
    if not src.any():
        return
    ext = _etendue(field)
    pos = (src > 0).astype(float)
    neg = (src < 0).astype(float)
    if pos.any():
        ax.contourf(pos, levels=[0.5, 2.0], colors=["#ff4d4d"], alpha=0.22,
                    extent=ext)
        ax.contour(pos, levels=[0.5], colors="#b30000", linewidths=1.4,
                   extent=ext)
    if neg.any():
        ax.contourf(neg, levels=[0.5, 2.0], colors=["#4d8bff"], alpha=0.22,
                    extent=ext)
        ax.contour(neg, levels=[0.5], colors="#0033b3", linewidths=1.4,
                   extent=ext)


def _overlay_materiaux(ax, field):
    kappa = np.asarray(getattr(field, "kappa", np.ones(field.shape)))
    if kappa.shape != field.shape:
        return
    fond = float(np.median(kappa))
    masque = ~np.isclose(kappa, fond)
    if not masque.any():
        return
    image = np.where(masque, 1.0, np.nan)
    ax.imshow(image, origin="lower", cmap="Greens", vmin=0.0, vmax=1.3,
              alpha=0.55, extent=_etendue(field))
    ax.contour(masque.astype(float), levels=[0.5], colors="#22c55e",
               linewidths=1.5, extent=_etendue(field))


def plot_apercu_scene(ax, field, titre):
    L = float(getattr(field, "taille_domaine", 1.0) or 1.0)
    ax.set_xlim(0.0, L)
    ax.set_ylim(0.0, L)
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.45, alpha=0.25)
    _overlay_materiaux(ax, field)
    _overlay_solides(ax, field)
    _overlay_sources(ax, field)
    _overlay_electrodes(ax, field)
    couleurs = {
        "dirichlet": "#ef4444", "neumann": "#94a3b8",
        "robin": "#22c55e", "radiation": "#f59e0b", "flux": "#eab308",
    }
    murs = getattr(field, "walls", {}) or {}
    segments = {
        "bas": ([0, L], [0, 0]), "haut": ([0, L], [L, L]),
        "gauche": ([0, 0], [0, L]), "droite": ([L, L], [0, L]),
    }
    for cote, (xs, ys) in segments.items():
        type_paroi = (murs.get(cote) or ("neumann",))[0]
        ax.plot(xs, ys, color=couleurs.get(type_paroi, "#94a3b8"),
                linewidth=3.0, solid_capstyle="butt")
    ax.set_title(f"Aperçu 2D — {titre}")
    _axes_metres(ax)


def plot_carte(ax, field, scalaire, levels=20):
    ext = _etendue(field)
    im = ax.imshow(field.V, origin="lower", cmap="plasma", aspect="equal",
                   extent=ext)
    ax.contour(_valeurs_sans_objets(field), levels=levels,
               colors="k", linewidths=0.4, alpha=0.4,
               extent=ext)
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    _overlay_sources(ax, field)
    _overlay_materiaux(ax, field)
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=scalaire)
    ax.set_title(scalaire)
    _axes_metres(ax)


def plot_isovaleurs(ax, field, scalaire, levels=20):
    cs = ax.contour(_valeurs_sans_objets(field), levels=levels,
                    cmap="viridis", linewidths=0.8,
                    extent=_etendue(field))
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.1f")
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    ax.set_aspect("equal")
    ax.set_title(f"Iso-valeurs ({scalaire})")
    _axes_metres(ax)


def plot_fleches(ax, field, champ_fn, champ, step=6):
    Fx, Fy, mag = champ_fn(field)
    X, Y = _grilles_metres(field)
    s = slice(None, None, step)
    ax.quiver(X[s, s], Y[s, s], Fx[s, s], Fy[s, s], mag[s, s], cmap="RdBu_r")
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    ax.set_aspect("equal")
    ax.set_title(f"{champ} (flèches)")
    _axes_metres(ax)


def plot_lignes(ax, field, champ_fn, scalaire, density=1.3):
    Fx, Fy, mag = champ_fn(field)
    X, Y = _grilles_metres(field)
    ax.imshow(field.V, origin="lower", cmap="RdBu_r", aspect="equal",
              alpha=0.85, extent=_etendue(field))
    ax.streamplot(X, Y, Fx, Fy, color="k", density=density,
                  linewidth=0.6, arrowsize=0.7)
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    _overlay_sources(ax, field)
    ax.set_title(f"Lignes de champ (fond : {scalaire})")
    _axes_metres(ax)


def plot_intensite(ax, field, champ_fn, champ):
    _, _, mag = champ_fn(field)
    im = ax.imshow(mag, origin="lower", cmap="inferno", aspect="equal",
                   extent=_etendue(field))
    _overlay_solides(ax, field)
    _overlay_sources(ax, field)
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=f"|{champ}|")
    ax.set_title(f"Intensité : |{champ}|")
    _axes_metres(ax)


def dessiner(ax, field, kind, champ_fn=champ_electrique, scalaire="V", champ="E"):
    if kind == "Carte scalaire":
        plot_carte(ax, field, scalaire)
    elif kind == "Iso-valeurs":
        plot_isovaleurs(ax, field, scalaire)
    elif kind == "Champ (flèches)":
        plot_fleches(ax, field, champ_fn, champ)
    elif kind == "Lignes de champ":
        plot_lignes(ax, field, champ_fn, scalaire)
    elif kind == "Intensité du champ":
        plot_intensite(ax, field, champ_fn, champ)
    else:
        raise KeyError(f"Vue inconnue : {kind!r}")


def dessiner_calques(ax, field, calques, champ_fn=champ_electrique,
                     scalaire="V", champ="E", fond_intensite=False):
    ext = _etendue(field)
    Fx, Fy, magnitude = champ_fn(field)
    if calques.get("carte", True):
        valeurs = magnitude if fond_intensite else field.V
        titre_barre = f"|{champ}|" if fond_intensite else scalaire
        im = ax.imshow(
            valeurs, origin="lower",
            cmap="inferno" if fond_intensite else "plasma",
            aspect="equal", extent=ext, alpha=0.88)
        ax.figure.colorbar(
            im, ax=ax, fraction=0.046, pad=0.04, label=titre_barre)
    if calques.get("iso", False):
        valeurs_iso = _valeurs_sans_objets(field)
        if np.ptp(valeurs_iso.compressed()) > 1e-14:
            contours = ax.contour(
                valeurs_iso, levels=16, cmap="viridis",
                linewidths=0.9, extent=ext)
            ax.clabel(contours, inline=True, fontsize=7, fmt="%.3g")
    X, Y = _grilles_metres(field)
    if calques.get("lignes", False):
        ax.streamplot(
            X, Y, Fx, Fy, color=magnitude, cmap="viridis",
            density=1.25, linewidth=0.8, arrowsize=0.8)
    if calques.get("fleches", False):
        pas = max(1, min(field.shape) // 22)
        s = slice(None, None, pas)
        ax.quiver(
            X[s, s], Y[s, s], Fx[s, s], Fy[s, s], magnitude[s, s],
            cmap="RdBu_r", alpha=0.9)
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    _overlay_sources(ax, field)
    _overlay_materiaux(ax, field)
    actifs = [nom for nom, actif in calques.items() if actif]
    ax.set_title(" + ".join(actifs) if actifs else "Objets du domaine")
    ax.set_aspect("equal")
    _axes_metres(ax)
