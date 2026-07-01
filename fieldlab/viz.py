import numpy as np

from fieldlab.field import champ_electrique

KINDS = [
    "Carte scalaire",
    "Iso-valeurs",
    "Champ (fleches)",
    "Lignes de champ",
    "Intensite du champ",
]


def _overlay_solides(ax, field):
    if field.solid_mask.any():
        gris = np.where(field.solid_mask, 1.0, np.nan)
        ax.imshow(gris, origin="lower", cmap="Greys", vmin=0, vmax=1.4, alpha=0.9)


def _overlay_electrodes(ax, field):
    """Souligne les points fixes interieurs (electrodes / temperatures imposees)
    par un double contour blanc+noir, visible sur tout fond. On exclut le bord."""
    elec = field.fixed_mask.copy()
    elec[0, :] = elec[-1, :] = elec[:, 0] = elec[:, -1] = False
    if not elec.any():
        return
    m = elec.astype(float)
    ax.contour(m, levels=[0.5], colors="white", linewidths=2.6, alpha=0.9)
    ax.contour(m, levels=[0.5], colors="black", linewidths=1.3)


def _overlay_sources(ax, field):
    """Materialise les regions sources, avec le SIGNE :
    rouge = source positive (courant sortant / chaleur injectee),
    bleu  = source negative (courant entrant / puits)."""
    src = field.source
    if not src.any():
        return
    pos = (src > 0).astype(float)
    neg = (src < 0).astype(float)
    if pos.any():
        ax.contourf(pos, levels=[0.5, 2.0], colors=["#ff4d4d"], alpha=0.22)
        ax.contour(pos, levels=[0.5], colors="#b30000", linewidths=1.4)
    if neg.any():
        ax.contourf(neg, levels=[0.5, 2.0], colors=["#4d8bff"], alpha=0.22)
        ax.contour(neg, levels=[0.5], colors="#0033b3", linewidths=1.4)


def plot_carte(ax, field, scalaire, levels=20):
    im = ax.imshow(field.V, origin="lower", cmap="plasma", aspect="equal")
    ax.contour(field.V, levels=levels, colors="k", linewidths=0.4, alpha=0.4)
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    _overlay_sources(ax, field)
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=scalaire)
    ax.set_title(scalaire)


def plot_isovaleurs(ax, field, scalaire, levels=20):
    cs = ax.contour(field.V, levels=levels, cmap="viridis", linewidths=0.8)
    ax.clabel(cs, inline=True, fontsize=6, fmt="%.1f")
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    ax.set_aspect("equal")
    ax.set_title(f"Iso-valeurs ({scalaire})")


def plot_fleches(ax, field, champ_fn, champ, step=6):
    Fx, Fy, mag = champ_fn(field)
    ny, nx = field.shape
    Y, X = np.mgrid[0:ny, 0:nx]
    s = slice(None, None, step)
    ax.quiver(X[s, s], Y[s, s], Fx[s, s], Fy[s, s], mag[s, s], cmap="RdBu_r")
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    ax.set_aspect("equal")
    ax.set_title(f"{champ} (fleches)")


def plot_lignes(ax, field, champ_fn, scalaire, density=1.3):
    Fx, Fy, mag = champ_fn(field)
    ny, nx = field.shape
    Y, X = np.mgrid[0:ny, 0:nx]
    ax.imshow(field.V, origin="lower", cmap="RdBu_r", aspect="equal", alpha=0.85)
    ax.streamplot(X, Y, Fx, Fy, color="k", density=density,
                  linewidth=0.6, arrowsize=0.7)
    _overlay_solides(ax, field)
    _overlay_electrodes(ax, field)
    _overlay_sources(ax, field)
    ax.set_title(f"Lignes de champ (fond : {scalaire})")


def plot_intensite(ax, field, champ_fn, champ):
    _, _, mag = champ_fn(field)
    im = ax.imshow(mag, origin="lower", cmap="inferno", aspect="equal")
    _overlay_solides(ax, field)
    _overlay_sources(ax, field)
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=f"|{champ}|")
    ax.set_title(f"Intensite : |{champ}|")


def dessiner(ax, field, kind, champ_fn=champ_electrique, scalaire="V", champ="E"):
    if kind == "Carte scalaire":
        plot_carte(ax, field, scalaire)
    elif kind == "Iso-valeurs":
        plot_isovaleurs(ax, field, scalaire)
    elif kind == "Champ (fleches)":
        plot_fleches(ax, field, champ_fn, champ)
    elif kind == "Lignes de champ":
        plot_lignes(ax, field, champ_fn, scalaire)
    elif kind == "Intensite du champ":
        plot_intensite(ax, field, champ_fn, champ)
    else:
        raise KeyError(f"Vue inconnue : {kind!r}")
