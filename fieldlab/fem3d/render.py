from dataclasses import dataclass, field as dataclass_field

import numpy as np
import pyvista as pv

from fieldlab.fem3d.calques import (
    CalquesRendu3D, OptionsGraines3D, calques_depuis_mode,
    points_graines_ligne, points_graines_volumiques, sous_echantillonner,
)
from fieldlab.fem3d.derived import gradient_elements
from fieldlab.fem3d import lignes_coupe as lc
from fieldlab.fem3d.rendu_p3 import (
    courbe_opacite, niveaux_isosurfaces, niveaux_isosurfaces_geometriques,
)
from fieldlab.fem3d.scene import ItemGeometrie
from fieldlab.fem3d.scene_editor import centre_item




MODES_RENDU = (
    "Carte scalaire", "Iso-valeurs", "Champ (flèches)",
    "Lignes de champ",
)
SCALAIRES_3D = (
    "Scalaire principal", "Intensité du champ", "Coefficient matériau κ",
)



VUES = MODES_RENDU + ("Plan de coupe", "Intensité du champ")

_LONGUEUR_MAX_GLYPHE = 0.12




_VTK_TETRA = 10


@dataclass(frozen=True)
class ScalaireAffiche3D:
    points: np.ndarray
    valeurs: np.ndarray
    libelle: str
    grille: object
    nom_tableau: str

    def valeur_au_point(self, point):
        p = np.asarray(point, dtype=float).reshape(1, 3)
        try:
            echantillon = pv.PolyData(p).sample(self.grille)
            valide = (echantillon["vtkValidPointMask"]
                       if "vtkValidPointMask" in echantillon.array_names
                       else None)
            if valide is None or bool(valide[0]):
                return float(echantillon[self.nom_tableau][0]), p[0]
        except (KeyError, TypeError, ValueError, RuntimeError):
            pass
        idx = int(np.argmin(np.sum((self.points - p[0]) ** 2, axis=1)))
        return float(self.valeurs[idx]), self.points[idx]


@dataclass
class PlanCoupe3D:
    normale: tuple = (1.0, 0.0, 0.0)
    origine: tuple = (0.5, 0.5, 0.5)


@dataclass
class OptionsCoupe3D:
    active: bool = False
    plans: list = dataclass_field(default_factory=list)
    fond_scalaire: bool = True
    isolignes: bool = True
    vecteurs_projetes: bool = False
    lignes_champ: bool = False
    orientation_libre: bool = False
    clip_boite: bool = False
    bornes_clip: tuple = None
    manipuler_widget: bool = False


@dataclass
class SourceLignes3D:
    centre: tuple = None
    normale: tuple = (0.0, 0.0, 1.0)


@dataclass
class OptionsRendu3D:
    courbe_volume: str = "Sigmoïde"
    nombre_isosurfaces: int = 8
    fraction_iso_min: float = 0.05
    fraction_iso_max: float = 0.95
    pas_glyphes: int = 4
    taille_glyphes: float = 0.12
    source_lignes: SourceLignes3D = dataclass_field(
        default_factory=SourceLignes3D)
    taille_source_lignes: float = 0.55
    densite_lignes: int = 7
    rayon_tubes: float = 0.004



    graines: OptionsGraines3D = dataclass_field(
        default_factory=OptionsGraines3D)


def _tetraedres_orientes(mesh) -> np.ndarray:
    t = mesh.t.T
    p = mesh.p.T
    p0, p1, p2, p3 = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]], p[t[:, 3]]
    volume6 = np.einsum("ij,ij->i", p1 - p0, np.cross(p2 - p0, p3 - p0))
    t = t.copy()
    inverses = volume6 < 0
    t[inverses, 2], t[inverses, 3] = t[inverses, 3], t[inverses, 2]
    return t


def construire_grille(field, scalaire: str = "V") -> pv.UnstructuredGrid:
    mesh = field.mesh
    t = _tetraedres_orientes(mesh)
    n_elements = t.shape[0]
    connectivite = np.hstack([
        np.full((n_elements, 1), 4, dtype=np.int64), t.astype(np.int64),
    ]).ravel()
    types_cellules = np.full(n_elements, _VTK_TETRA, dtype=np.uint8)
    points = mesh.p.T.astype(np.float64)

    grille = pv.UnstructuredGrid(connectivite, types_cellules, points)
    grille[scalaire] = field.V
    return grille


def construire_coupe(field, normal=(1.0, 0.0, 0.0), origine=None,
                      scalaire: str = "V") -> pv.PolyData:
    if origine is None:
        origine = tuple(field.mesh.p.mean(axis=1))
    return construire_grille(field, scalaire).slice(normal=normal, origin=origine)


def construire_isosurfaces(field, valeurs=None, n: int = 8,
                            scalaire: str = "V") -> pv.PolyData:
    grille = construire_grille(field, scalaire)
    if valeurs is not None:
        return grille.contour(isosurfaces=list(valeurs), scalars=scalaire)
    return grille.contour(isosurfaces=n, scalars=scalaire)


def construire_grille_vectorielle(field, kappa_pondere: bool = False,
                                   nom: str = "champ") -> pv.UnstructuredGrid:
    if field.vecteurs is not None:
        grille_pt = construire_grille(field)
        grille_pt[nom] = field.vecteurs
        grille_pt[f"|{nom}|"] = np.linalg.norm(field.vecteurs, axis=1)
        return grille_pt
    grad = gradient_elements(field)
    vecteurs = -grad
    if kappa_pondere:
        kappa_elem = field.kappa[field.mesh.t].mean(axis=0)
        vecteurs = vecteurs * kappa_elem[:, None]
    grille = construire_grille(field)
    grille[nom] = vecteurs
    grille_pt = grille.cell_data_to_point_data()
    grille_pt[f"|{nom}|"] = np.linalg.norm(grille_pt[nom], axis=1)
    return grille_pt


def _preparer_scalaire_3d(field, selection: str, scalaire: str,
                           libelle_champ: str, libelle_kappa: str,
                           kappa_pondere: bool,
                           besoin_vecteurs: bool = False):
    grille_principale = construire_grille(field, scalaire)
    selection = selection or "Scalaire principal"
    aliases = {
        "principal": "Scalaire principal",
        "intensite": "Intensité du champ",
        "kappa": "Coefficient matériau κ",
    }
    selection = aliases.get(selection, selection)
    if selection not in SCALAIRES_3D:
        raise KeyError(
            f"Scalaire 3D inconnu : {selection!r}. Choix : {SCALAIRES_3D}")

    grille_vectorielle = None
    if besoin_vecteurs or selection == "Intensité du champ":
        grille_vectorielle = construire_grille_vectorielle(
            field, kappa_pondere=kappa_pondere)

    if selection == "Intensité du champ":
        grille_scalaire = grille_vectorielle
        nom_scalaire = "|champ|"
        valeurs = np.asarray(grille_scalaire[nom_scalaire])
        libelle = (getattr(field, "libelle_scalaire", None)
                   if field.vecteurs is not None else None) \
            or libelle_champ or "Intensité du champ"
    elif selection == "Coefficient matériau κ":
        grille_scalaire = grille_principale.copy()
        nom_scalaire = "kappa"
        grille_scalaire[nom_scalaire] = np.asarray(field.kappa)
        valeurs = np.asarray(field.kappa)
        libelle = libelle_kappa or "Coefficient matériau κ"
    else:
        grille_scalaire = grille_principale
        nom_scalaire = scalaire
        valeurs = np.asarray(field.V)
        libelle = scalaire
    return (grille_principale, grille_scalaire, grille_vectorielle,
            nom_scalaire, valeurs, libelle)


def construire_glyphes(field, kappa_pondere: bool = False, pas: int = 4,
                        nom: str = "champ",
                        grille_pt: pv.UnstructuredGrid = None,
                        scalaire_couleur=None,
                        nom_scalaire: str = None,
                        taille_relative: float = _LONGUEUR_MAX_GLYPHE,
                        normaliser: bool = True) -> pv.PolyData:
    if grille_pt is None:
        grille_pt = construire_grille_vectorielle(field, kappa_pondere, nom)
    idx = np.arange(0, grille_pt.n_points, pas)
    nuage = pv.PolyData(grille_pt.points[idx])
    nuage[nom] = grille_pt[nom][idx]
    mag = grille_pt[f"|{nom}|"][idx]
    nuage[f"|{nom}|"] = mag
    if scalaire_couleur is not None and nom_scalaire:
        nuage[nom_scalaire] = np.asarray(scalaire_couleur)[idx]





    echelle_mag = (np.minimum(mag, float(np.percentile(mag, 98.0)))
                   if mag.size else mag)
    nuage["__echelle_glyphes"] = echelle_mag
    mmax = float(echelle_mag.max()) if echelle_mag.size else 0.0
    etendue = field.mesh.p.max(axis=1) - field.mesh.p.min(axis=1)
    longueur_max = float(taille_relative) * float(np.max(etendue))
    if normaliser:
        facteur = longueur_max / mmax if mmax > 1e-12 else 0.0
        echelle = "__echelle_glyphes"
    else:
        facteur, echelle = longueur_max, False
    return nuage.glyph(
        orient=nom, scale=echelle, factor=facteur, geom=pv.Arrow())


def construire_streamlines(field, kappa_pondere: bool = False,
                            source_center=None, source_radius: float = None,
                            n_points: int = 60, max_length: float = None,
                            nom: str = "champ",
                            grille_pt: pv.UnstructuredGrid = None,
                            source=None) -> pv.PolyData:
    if grille_pt is None:
        grille_pt = construire_grille_vectorielle(field, kappa_pondere, nom)
    if source_center is None:
        source_center = tuple(field.mesh.p.mean(axis=1))
    if source_radius is None:
        etendue = field.mesh.p.max(axis=1) - field.mesh.p.min(axis=1)
        source_radius = 0.4 * float(np.linalg.norm(etendue))
    if max_length is None:
        etendue = field.mesh.p.max(axis=1) - field.mesh.p.min(axis=1)
        max_length = 3.0 * float(np.max(etendue))
    if source is not None:
        kwargs = {
            "vectors": nom, "integration_direction": "both",
            "initial_step_length": 0.25, "max_steps": 2000,
            "compute_vorticity": False,
        }
        try:
            return grille_pt.streamlines_from_source(
                source, max_length=max_length, **kwargs)
        except TypeError:


            return grille_pt.streamlines_from_source(
                source, max_time=max_length, **kwargs)
    return grille_pt.streamlines(nom, source_center=source_center,
                                  source_radius=source_radius,
                                  n_points=n_points, max_length=max_length)


def _carte_couleurs(valeurs: np.ndarray):
    valeurs = np.asarray(valeurs, dtype=float)
    vmin, vmax = float(np.min(valeurs)), float(np.max(valeurs))
    amplitude = max(abs(vmin), abs(vmax))
    if amplitude <= 0 or np.isclose(vmin, vmax):






        delta = max(1.0, 0.05 * amplitude)
        return "inferno", (vmax - delta, vmax + delta), False
    p2, p98 = (float(v) for v in np.percentile(valeurs, [2.0, 98.0]))
    if not p98 > p2:
        p2, p98 = vmin, vmax
    if vmin < -0.02 * amplitude and vmax > 0.02 * amplitude:
        amplitude_robuste = max(abs(p2), abs(p98)) or amplitude
        return "coolwarm", (-amplitude_robuste, amplitude_robuste), False
    if vmin >= 0.0:
        positifs = valeurs[valeurs > 0.0]
        if positifs.size >= 8:
            p2p, mediane, p98p = (float(v) for v in np.percentile(
                positifs, [2.0, 50.0, 98.0]))





            if p98p > 8.0 * mediane and p98p > p2p:







                return "inferno", (max(p2p, 1e-4 * p98p), p98p), True
    return "inferno", (p2, p98), False


def _args_barre(titre: str, theme_sombre: bool = False) -> dict:
    arguments = {
        "title": titre,
        "n_labels": 5,
        "fmt": "%.3g",
        "title_font_size": 12,
        "label_font_size": 10,
        "color": "#f8fafc" if theme_sombre else "#111827",
        "vertical": False,
        "position_x": 0.27,
        "position_y": 0.035,
        "width": 0.55,
        "height": 0.075,
        "fill": not theme_sombre,
    }
    if not theme_sombre:
        arguments["background_color"] = "#ffffff"
    return arguments


def _maillage_item(item: ItemGeometrie):
    p = item.params
    if item.forme == "boite":
        if all(nom in p for nom in ("cx", "cy", "cz", "lx", "ly", "lz")):
            bounds = (-p["lx"] / 2, p["lx"] / 2,
                      -p["ly"] / 2, p["ly"] / 2,
                      -p["lz"] / 2, p["lz"] / 2)
            maillage = pv.Box(bounds=bounds)
            maillage.translate((p["cx"], p["cy"], p["cz"]), inplace=True)
        else:
            bounds = (p["x0"], p["x1"], p["y0"], p["y1"],
                      p["z0"], p["z1"])
            maillage = pv.Box(bounds=bounds)
        centre = centre_item(item)
    if item.forme == "sphere":
        maillage = pv.Sphere(
            radius=p["r"], center=(p["cx"], p["cy"], p["cz"]),
            theta_resolution=36, phi_resolution=24)
        centre = centre_item(item)
    if item.forme == "cylindre":
        directions = {
            "x": (1.0, 0.0, 0.0),
            "y": (0.0, 1.0, 0.0),
            "z": (0.0, 0.0, 1.0),
        }
        maillage = pv.Cylinder(
            center=(p["cx"], p["cy"], p["cz"]),
            direction=directions[p.get("axe", "z")],
            radius=p["r"], height=p["longueur"],
            resolution=48, capping=True)
        centre = centre_item(item)
    if item.forme == "maillage_importe":
        maillage = p.get("maillage")
        if maillage is None:
            chemin = p.get("chemin")
            if not (chemin and str(chemin).lower().endswith(".stl")):
                return None
            try:
                maillage = pv.read(chemin)
            except (OSError, RuntimeError, ValueError):
                return None



        maillage = maillage.copy()
        echelle = float(p.get("echelle", 1.0))
        if not np.isclose(echelle, 1.0):
            maillage.scale(echelle, inplace=True)
        decalage = np.asarray(p.get("decalage", (0.0, 0.0, 0.0)), dtype=float)
        if np.any(decalage):
            maillage.translate(decalage, inplace=True)
        if np.allclose(item.rotation, 0.0):
            return maillage
        centre = tuple(maillage.center)
        maillage.rotate_x(item.rotation[0], point=centre, inplace=True)
        maillage.rotate_y(item.rotation[1], point=centre, inplace=True)
        maillage.rotate_z(item.rotation[2], point=centre, inplace=True)
        return maillage
    if item.forme not in ("boite", "sphere", "cylindre"):
        return None
    if not np.allclose(item.rotation, 0.0):
        maillage.rotate_x(item.rotation[0], point=centre, inplace=True)
        maillage.rotate_y(item.rotation[1], point=centre, inplace=True)
        maillage.rotate_z(item.rotation[2], point=centre, inplace=True)
    return maillage


def _borner_maillage_visuel(maillage, bounds):
    if maillage is None:
        return None
    try:
        bornes = maillage.bounds
        deborde = any((bornes[2 * axe] < bounds[2 * axe]
                       or bornes[2 * axe + 1] > bounds[2 * axe + 1])
                      for axe in range(3))
        if deborde:
            maillage = maillage.clip_box(bounds=bounds, invert=False)
        return maillage if maillage.n_cells > 0 else None
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return maillage


def _tube_circuit_dans_domaine(points, bounds, rayon):
    ligne = pv.lines_from_points(points, close=False)
    try:
        bornes = ligne.bounds
        deborde = any((bornes[2 * axe] < bounds[2 * axe]
                       or bornes[2 * axe + 1] > bounds[2 * axe + 1])
                      for axe in range(3))
        if deborde:
            ligne = ligne.clip_box(bounds=bounds, invert=False)
            ligne = ligne.extract_surface(algorithm=None)
        if ligne.n_cells == 0:
            return None
        return ligne.tube(radius=rayon, n_sides=20, capping=True)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None


def _ajouter_masque_scene(plotter, grille, masque, nom, couleur, label):
    masque = np.asarray(masque, dtype=bool)
    if masque.shape != (grille.n_points,) or not masque.any():
        return False
    travail = grille.copy()
    travail[nom] = masque.astype(np.uint8)
    extrait = travail.threshold(0.5, scalars=nom, preference="point")
    if extrait.n_cells == 0:
        return False
    plotter.add_mesh(
        extrait.extract_surface(algorithm="dataset_surface"),
        color=couleur, opacity=0.58, ambient=0.65, diffuse=0.55,
        show_edges=True, line_width=1, show_scalar_bar=False, label=label)
    return True


def _ajouter_repli_masques(plotter, field, grille):
    ajoutes = 0
    fixed = getattr(field, "fixed_mask", np.zeros(grille.n_points, dtype=bool))
    solid = getattr(field, "solid_mask", np.zeros(grille.n_points, dtype=bool))
    source = getattr(field, "source", np.zeros(grille.n_points))
    kappa = getattr(field, "kappa", np.ones(grille.n_points))
    ajoutes += _ajouter_masque_scene(
        plotter, grille, fixed, "__scene_fixed", "#dc2626", "Valeur imposée")
    ajoutes += _ajouter_masque_scene(
        plotter, grille, solid, "__scene_solid", "#94a3b8", "Isolant")
    if np.asarray(kappa).shape == (grille.n_points,):
        fond = float(np.median(kappa))
        materiaux = ~np.isclose(kappa, fond)
        ajoutes += _ajouter_masque_scene(
            plotter, grille, materiaux, "__scene_kappa",
            "#16a34a", "Matériau")
    ajoutes += _ajouter_masque_scene(
        plotter, grille, np.asarray(source) != 0, "__scene_source",
        "#f59e0b", "Source volumique")
    return ajoutes


def _dessiner_scene(plotter, field, grille, info_scalaire,
                    note_echelle: str = "", objets: bool = True,
                    theme_sombre: bool = False):
    scene = getattr(field, "scene", None)
    if scene is not None:
        bounds = scene.bornes_vtk
        dimensions = scene.dimensions
        items = scene.items
        circuits = scene.circuits
    else:
        bounds = grille.bounds
        dimensions = np.array([
            bounds[1] - bounds[0], bounds[3] - bounds[2],
            bounds[5] - bounds[4]])
        items, circuits = [], []
    if not objets:
        items, circuits = [], []

    label_domaine = (
        f"Domaine {dimensions[0]:.3g}×{dimensions[1]:.3g}×"
        f"{dimensions[2]:.3g} m")
    plotter.add_mesh(
        pv.Box(bounds=bounds), style="wireframe",
        color="#8b98ad" if theme_sombre else "#475569",
        line_width=2, show_scalar_bar=False, label=label_domaine,
        name="boite_domaine")

    for item in items:
        maillage = _borner_maillage_visuel(_maillage_item(item), bounds)
        if maillage is None:
            continue
        role = str(getattr(item, "role", "")).lower()
        opacite_objet = 0.82 if role in (
            "electrode", "temperature", "source", "isolant") else 0.62
        plotter.add_mesh(
            maillage, color=item.couleur, opacity=opacite_objet,
            ambient=0.65, diffuse=0.55, specular=0.15,
            show_edges=True, edge_color="#dbeafe", line_width=1,
            show_scalar_bar=False,
            label=item.libelle_legende())

    n_repli = 0
    if objets and not items:
        n_repli = _ajouter_repli_masques(plotter, field, grille)

    rayon_tube = 0.012 * float(np.linalg.norm(dimensions))
    for i, circuit in enumerate(circuits):
        points_circuit = getattr(circuit, "points", circuit)
        tube = _tube_circuit_dans_domaine(
            points_circuit, bounds, rayon_tube)
        if tube is None:
            continue
        plotter.add_mesh(
            tube, color=getattr(circuit, "couleur", "#f97316"),
            smooth_shading=True, ambient=0.8, diffuse=0.6, specular=0.25,
            show_edges=True, edge_color="#f8fafc", line_width=0.5,
            show_scalar_bar=False,
            label=getattr(circuit, "label", f"Circuit {i + 1}"))

    if hasattr(plotter, "add_legend"):
        n_entrees = 1 + len(items) + len(circuits) + n_repli
        hauteur = min(0.45, max(0.12, 0.045 * n_entrees))
        plotter.add_legend(
            border=True, bcolor="#151b2b" if theme_sombre else "white",
            size=(0.30, hauteur))

    valeurs = np.asarray(info_scalaire.valeurs)
    hud = (
        f"Domaine : {dimensions[0]:.3g} × {dimensions[1]:.3g} × "
        f"{dimensions[2]:.3g} m\n"
        f"{info_scalaire.libelle} : min {np.min(valeurs):.4g}  "
        f"max {np.max(valeurs):.4g}")
    if note_echelle:
        hud += f"\n{note_echelle}"
    if hasattr(plotter, "add_text"):
        plotter.add_text(
            hud, position="upper_left", font_size=9,
            color="#e6edf7" if theme_sombre else "#111827")


def dessiner_scene_seule(plotter, scene, index_selectionne=None,
                         theme_sombre=False):
    plotter.clear()
    for nom_methode in (
            "clear_plane_widgets", "clear_box_widgets", "clear_line_widgets"):
        if hasattr(plotter, nom_methode):
            try:
                getattr(plotter, nom_methode)()
            except Exception:
                pass
    correspondance = {}
    plotter.add_mesh(
        pv.Box(bounds=scene.bornes_vtk), style="wireframe",
        color="#8b98ad" if theme_sombre else "#475569",
        line_width=2, show_scalar_bar=False,
        label=(f"Domaine {scene.dimensions[0]:.3g}×"
               f"{scene.dimensions[1]:.3g}×{scene.dimensions[2]:.3g} m"))
    erreur_cao = None
    if scene.a_geometrie_cao:
        try:
            from fieldlab.fem3d.mesh_gmsh import surface_scene_cao
            points, triangles = surface_scene_cao(
                scene, scene.taille_maille_cao)
            faces = np.column_stack((
                np.full(len(triangles), 3, dtype=np.int64), triangles)).ravel()
            surface = pv.PolyData(points, faces)
            plotter.add_mesh(
                surface, color="#64748b", opacity=0.42, show_edges=True,
                show_scalar_bar=False, label="Résultat CAO exact",
                name="scene_resultat_cao", pickable=False)
        except (ImportError, OSError, RuntimeError, ValueError) as erreur:
            erreur_cao = str(erreur)
    for index, item in enumerate(scene.items):
        if scene.a_geometrie_cao and item.operation_cao != "aucune" \
                and erreur_cao is None:
            continue
        maillage = _borner_maillage_visuel(
            _maillage_item(item), scene.bornes_vtk)
        if maillage is None:
            continue
        acteur = plotter.add_mesh(
            maillage, color=item.couleur,
            opacity=0.90 if index == index_selectionne else 0.68,
            ambient=0.65, diffuse=0.55, specular=0.15,
            show_edges=True, edge_color="#dbeafe",
            line_width=3 if index == index_selectionne else 1,
            show_scalar_bar=False, label=item.libelle_legende(),
            name=f"scene_item_{item.identifiant}", pickable=True)
        if acteur is not None:
            correspondance[id(acteur)] = index
    rayon = 0.012 * float(np.linalg.norm(scene.dimensions))
    decalage = len(scene.items)
    for i, circuit in enumerate(scene.circuits):
        tube = _tube_circuit_dans_domaine(
            circuit.points, scene.bornes_vtk, rayon)
        if tube is None:
            continue
        index = decalage + i
        acteur = plotter.add_mesh(
            tube, color=circuit.couleur, smooth_shading=True,
            ambient=0.8, diffuse=0.6, specular=0.25,
            show_edges=True, edge_color="#f8fafc",
            line_width=3 if index == index_selectionne else 1,
            show_scalar_bar=False,
            label=f"{circuit.label} — I={circuit.courant:g} A",
            name=f"scene_circuit_{circuit.identifiant}", pickable=True)
        if acteur is not None:
            correspondance[id(acteur)] = index
    if hasattr(plotter, "add_legend"):
        nombre = 1 + len(scene.items) + len(scene.circuits)
        plotter.add_legend(
            border=True,
            bcolor="#151b2b" if theme_sombre else "white",
            size=(0.30, min(0.42, max(0.12, 0.045 * nombre))))
    if hasattr(plotter, "add_text"):
        plotter.add_text(
            "APERÇU — calcul non lancé\n"
            f"Milieu ambiant : {scene.materiau_ambiant}\n"
            f"{len(scene.items)} objet(s), {len(scene.circuits)} circuit(s)"
            + (f"\nCAO : {erreur_cao}" if erreur_cao else ""),
            position="upper_left", font_size=9,
            color="#e6edf7" if theme_sombre else "#111827")
    plotter.add_axes()
    try:
        plotter.show_grid(
            xtitle="x (m)", ytitle="y (m)", ztitle="z (m)")
    except TypeError:
        plotter.show_grid()
    try:
        plotter.reset_camera(bounds=scene.bornes_vtk)
    except TypeError:
        plotter.reset_camera()
    return correspondance


def _retirer_acteur(plotter, nom):
    if hasattr(plotter, "remove_actor"):
        try:
            plotter.remove_actor(
                nom, reset_camera=False, render=False)
        except (KeyError, RuntimeError, TypeError, ValueError):
            pass


def _preparer_zone_iso(field, grille_scalaire, grille_vectorielle=None):
    nombre = grille_scalaire.n_points
    fixes = np.asarray(
        getattr(field, "fixed_mask", np.zeros(nombre, dtype=bool)),
        dtype=bool)
    solides = np.asarray(
        getattr(field, "solid_mask", np.zeros(nombre, dtype=bool)),
        dtype=bool)
    if fixes.shape != (nombre,):
        fixes = np.zeros(nombre, dtype=bool)
    if solides.shape != (nombre,):
        solides = np.zeros(nombre, dtype=bool)
    actif = (~(fixes | solides)).astype(np.uint8)
    grille_scalaire["__zone_iso_active"] = actif
    if grille_vectorielle is not None:
        grille_vectorielle["__zone_iso_active"] = actif


def _exclure_objets_des_iso(maillage):
    if maillage is None or "__zone_iso_active" not in maillage.array_names:
        return maillage
    try:
        filtre = maillage.threshold(
            0.999, scalars="__zone_iso_active", preference="point",
            all_scalars=True)
        return filtre if filtre.n_cells > 0 else None
    except (KeyError, RuntimeError, TypeError, ValueError):
        return maillage


def _widgets_plans(plotter):
    conteneur = getattr(plotter, "widgets", None)
    if conteneur is not None and hasattr(conteneur, "plane_widgets"):
        return (list(conteneur.plane_widgets),
                list(getattr(conteneur, "plane_sliced_meshes", [])))
    return (list(getattr(plotter, "plane_widgets", [])),
            list(getattr(plotter, "plane_sliced_meshes", [])))


def _widgets_boites(plotter):
    conteneur = getattr(plotter, "widgets", None)
    if conteneur is not None and hasattr(conteneur, "box_widgets"):
        return list(conteneur.box_widgets)
    return list(getattr(plotter, "box_widgets", []))


def _ajouter_clip_boite(plotter, grille, options, **kwargs):
    if not options or not options.clip_boite \
            or not hasattr(plotter, "add_mesh_clip_box"):
        return plotter.add_mesh(grille, **kwargs)

    acteur = plotter.add_mesh_clip_box(
        grille, invert=False, rotation_enabled=False,
        outline_translation=True, interaction_event="always",
        factor=1.0, **kwargs)
    widgets = _widgets_boites(plotter)
    if not widgets:
        return acteur
    widget = widgets[-1]
    if options.bornes_clip is not None:
        try:
            widget.PlaceWidget(options.bornes_clip)
            widget.InvokeEvent("InteractionEvent")
        except (AttributeError, TypeError):
            pass

    def _memoriser_bornes(objet, _event):
        try:
            options.bornes_clip = tuple(float(v) for v in objet.GetBounds())
        except AttributeError:
            return

    try:
        widget.AddObserver("InteractionEvent", _memoriser_bornes)
    except AttributeError:
        pass
    return acteur


def _ajouter_volume(plotter, grille, nom_scalaire, cmap, clim,
                    opacites, barre, options_coupe, afficher_barre=True):
    kwargs = {
        "scalars": nom_scalaire, "cmap": cmap, "clim": clim,
        "opacity": opacites, "n_colors": 256, "shade": True,
        "scalar_bar_args": barre, "name": "volume_3d",
        "show_scalar_bar": bool(afficher_barre),
    }
    plotter.add_volume(grille, **kwargs)
    if not options_coupe or not options_coupe.clip_boite \
            or not hasattr(plotter, "add_box_widget"):
        return

    def _rogner(boite):
        bornes = tuple(float(v) for v in boite.bounds)
        options_coupe.bornes_clip = bornes
        try:
            extrait = grille.clip_box(bounds=bornes, invert=False)
            if extrait.n_cells > 0:
                plotter.add_volume(extrait, **kwargs)
            else:
                _retirer_acteur(plotter, "volume_3d")
        except (RuntimeError, TypeError, ValueError):
            return

    bornes_memorisees = options_coupe.bornes_clip
    widget = plotter.add_box_widget(
        _rogner, bounds=grille.bounds, factor=1.0,
        rotation_enabled=False, outline_translation=True,
        interaction_event="always", color="#64748b")
    if bornes_memorisees is not None:
        try:
            widget.PlaceWidget(bornes_memorisees)
            widget.InvokeEvent("InteractionEvent")
        except (AttributeError, TypeError):
            pass


def lignes_champ_dans_coupe(grille_vectorielle, normale, origine,
                            densite=7, resolution=48, nom="champ"):
    normale = np.asarray(normale, dtype=float)
    norme = float(np.linalg.norm(normale))
    if norme <= 1e-14:
        return pv.PolyData()
    normale = normale / norme
    u, v = lc.base_plan(normale)
    bounds = grille_vectorielle.bounds
    coins = np.array([[x, y, z]
                      for x in bounds[0:2]
                      for y in bounds[2:4]
                      for z in bounds[4:6]])
    centre_domaine = np.asarray(grille_vectorielle.center)
    origine = np.asarray(origine, dtype=float)


    centre_plan = centre_domaine + float(
        (origine - centre_domaine) @ normale) * normale
    su_coins = (coins - centre_plan) @ u
    sv_coins = (coins - centre_plan) @ v
    su = np.linspace(float(su_coins.min()), float(su_coins.max()),
                     int(resolution))
    sv = np.linspace(float(sv_coins.min()), float(sv_coins.max()),
                     int(resolution))
    SU, SV = np.meshgrid(su, sv, indexing="ij")
    points3d = (centre_plan[None, :]
                + SU.ravel()[:, None] * u[None, :]
                + SV.ravel()[:, None] * v[None, :])
    try:
        echantillon = pv.PolyData(points3d).sample(grille_vectorielle)
        vecteurs = np.asarray(echantillon[nom], dtype=float)
    except (KeyError, RuntimeError, TypeError, ValueError):
        return pv.PolyData()
    valide = np.ones(len(points3d), dtype=bool)
    if "vtkValidPointMask" in echantillon.array_names:
        valide &= np.asarray(echantillon["vtkValidPointMask"], dtype=bool)
    valide &= np.all(np.isfinite(vecteurs), axis=1)
    forme = (len(su), len(sv))
    champ2d = lc.ChampPlan2D(
        (vecteurs @ u).reshape(forme), (vecteurs @ v).reshape(forme),
        valide.reshape(forme), su, sv)
    graines = lc.graines_grille_plan(champ2d, cote=max(3, int(densite)))
    lignes2d = lc.integrer_lignes(champ2d, graines)
    lignes3d = lc.lignes_vers_3d(lignes2d, centre_plan, u, v)
    if not lignes3d:
        return pv.PolyData()
    points = np.vstack(lignes3d)
    cellules = []
    debut = 0
    for ligne in lignes3d:
        n = len(ligne)
        cellules.append(np.concatenate(([n], np.arange(debut, debut + n))))
        debut += n
    return pv.PolyData(points, lines=np.concatenate(cellules))


def _mettre_a_jour_superpositions_coupe(
        plotter, index, plan, coupe, grille_vectorielle,
        nom_scalaire, options, longueur_reference,
        echelle_log=False, clim=None, cmap="inferno",
        grille_scalaire=None, options_rendu=None):
    nom_isolignes = f"isolignes_coupe_{index}"
    if options.isolignes and coupe.n_points > 0:
        try:
            coupe_iso = _exclure_objets_des_iso(coupe)
            if coupe_iso is None:
                raise KeyError("Aucune cellule hors objet")
            valeurs = np.asarray(coupe_iso[nom_scalaire])
            isolignes = None
            if np.ptp(valeurs) > 1e-14:






                if echelle_log and clim and clim[0] > 0:
                    niveaux = np.geomspace(clim[0], clim[1], 12)
                    niveaux = niveaux[(niveaux >= valeurs.min())
                                      & (niveaux <= valeurs.max())]
                    if niveaux.size:
                        isolignes = coupe_iso.contour(
                            isosurfaces=list(niveaux), scalars=nom_scalaire)
                else:
                    isolignes = coupe_iso.contour(
                        isosurfaces=10, scalars=nom_scalaire)
            if isolignes is not None and isolignes.n_points > 0:
                plotter.add_mesh(
                    isolignes, color="#111827", line_width=1.5,
                    show_scalar_bar=False, name=nom_isolignes, render=False)
            else:
                _retirer_acteur(plotter, nom_isolignes)
        except (KeyError, RuntimeError, ValueError):
            _retirer_acteur(plotter, nom_isolignes)
    else:
        _retirer_acteur(plotter, nom_isolignes)

    nom_vecteurs = f"vecteurs_coupe_{index}"
    vecteurs_ok = False
    if options.vecteurs_projetes and grille_vectorielle is not None:
        normale = np.asarray(plan.normale, dtype=float)
        norme = float(np.linalg.norm(normale))
        if norme > 1e-14:
            normale = normale / norme
            coupe_vecteurs = grille_vectorielle.slice(
                normal=normale, origin=plan.origine)
            if coupe_vecteurs.n_points > 0:
                vecteurs = np.asarray(coupe_vecteurs["champ"])
                projetes = vecteurs - np.outer(
                    vecteurs @ normale, normale)
                magnitudes = np.linalg.norm(projetes, axis=1)
                pas = max(1, len(magnitudes) // 180)
                indices = np.arange(0, len(magnitudes), pas)
                maximum = float(np.max(magnitudes)) if len(magnitudes) else 0.0
                if maximum > 1e-14:
                    nuage = pv.PolyData(coupe_vecteurs.points[indices])
                    nuage["champ_projete"] = projetes[indices]
                    nuage["|champ_projete|"] = magnitudes[indices]
                    facteur = 0.08 * longueur_reference / maximum
                    glyphes = nuage.glyph(
                        orient="champ_projete", scale="|champ_projete|",
                        factor=facteur, geom=pv.Arrow())
                    plotter.add_mesh(
                        glyphes, scalars="|champ_projete|", cmap="viridis",
                        show_scalar_bar=False, name=nom_vecteurs,
                        render=False)
                    vecteurs_ok = True
    if not vecteurs_ok:
        _retirer_acteur(plotter, nom_vecteurs)




    nom_lignes = f"lignes_coupe_{index}"
    lignes_ok = False
    if options.lignes_champ and grille_vectorielle is not None:
        densite = (options_rendu.densite_lignes
                   if options_rendu is not None else 7)
        try:
            lignes = lignes_champ_dans_coupe(
                grille_vectorielle, plan.normale, plan.origine,
                densite=densite)
        except (RuntimeError, TypeError, ValueError):
            lignes = pv.PolyData()
        if lignes.n_points > 0:
            rayon = 0.0025 * longueur_reference
            if options_rendu is not None:
                rayon = max(1e-12, 0.7 * options_rendu.rayon_tubes
                            * longueur_reference)
            tubes = lignes.tube(radius=rayon, n_sides=8)
            kwargs = {"show_scalar_bar": False, "name": nom_lignes,
                      "lighting": False, "render": False}
            if grille_scalaire is not None:
                try:
                    tubes = tubes.sample(grille_scalaire)
                    kwargs.update({"scalars": nom_scalaire, "cmap": cmap,
                                   "clim": clim, "log_scale": echelle_log})
                except (KeyError, RuntimeError, TypeError, ValueError):
                    kwargs["color"] = "#0ea5e9"
            else:
                kwargs["color"] = "#0ea5e9"
            plotter.add_mesh(tubes, **kwargs)
            lignes_ok = True
    if not lignes_ok:
        _retirer_acteur(plotter, nom_lignes)


def _coupe_statique(grille_scalaire, plan):
    normale = np.asarray(plan.normale, dtype=float)
    norme = float(np.linalg.norm(normale))
    if norme <= 1e-14:
        return None
    normale = normale / norme
    origine = np.asarray(plan.origine, dtype=float)
    coupe = grille_scalaire.slice(normal=normale, origin=origine)
    if coupe.n_points > 0:
        return coupe
    bounds = grille_scalaire.bounds
    diagonale = float(np.linalg.norm([
        bounds[1] - bounds[0], bounds[3] - bounds[2],
        bounds[5] - bounds[4]]))
    centre = np.asarray(grille_scalaire.center)
    sens = 1.0 if float((centre - origine) @ normale) >= 0 else -1.0
    for epsilon in (1e-6, 1e-4, 1e-3):
        origine_essai = origine + sens * epsilon * diagonale * normale
        coupe = grille_scalaire.slice(normal=normale, origin=origine_essai)
        if coupe.n_points > 0:
            return coupe
    return None


def _ajouter_coupes(plotter, grille_scalaire, grille_vectorielle,
                     nom_scalaire, cmap, clim, barre, options,
                     afficher_barre=False, echelle_log=False,
                     options_rendu=None):
    if not options or not options.active:
        return
    if not options.plans:
        options.plans.append(PlanCoupe3D(
            origine=tuple(grille_scalaire.center)))
    bounds = grille_scalaire.bounds
    longueur_reference = max(
        bounds[1] - bounds[0], bounds[3] - bounds[2],
        bounds[5] - bounds[4])
    barre_coupe = dict(barre)

    if not options.manipuler_widget:
        for index, plan in enumerate(options.plans):
            coupe = _coupe_statique(grille_scalaire, plan)
            if coupe is None:
                _retirer_acteur(plotter, f"coupe_3d_{index}")
                continue
            if options.fond_scalaire:
                plotter.add_mesh(
                    coupe, scalars=nom_scalaire, cmap=cmap, clim=clim,
                    log_scale=echelle_log,
                    scalar_bar_args=barre_coupe,
                    show_scalar_bar=bool(afficher_barre and index == 0),
                    name=f"coupe_3d_{index}", render=False)
            else:
                plotter.add_mesh(
                    coupe, color="#94a3b8", opacity=0.15,
                    show_scalar_bar=False,
                    name=f"coupe_3d_{index}", render=False)
            _mettre_a_jour_superpositions_coupe(
                plotter, index, plan, coupe, grille_vectorielle,
                nom_scalaire, options, longueur_reference,
                echelle_log=echelle_log, clim=clim, cmap=cmap,
                grille_scalaire=grille_scalaire,
                options_rendu=options_rendu)
        return

    for index, plan in enumerate(options.plans):
        plotter.add_mesh_slice(
            grille_scalaire, normal=plan.normale, origin=plan.origine,
            scalars=nom_scalaire, cmap=cmap, clim=clim,
            log_scale=echelle_log,
            scalar_bar_args=barre_coupe,
            show_scalar_bar=bool(afficher_barre and index == 0),
            interaction_event="always",
            normal_rotation=options.orientation_libre,
            outline_translation=False,
            origin_translation=True,
            widget_color="#f59e0b",
            name=f"coupe_3d_{index}")
        widgets, coupes = _widgets_plans(plotter)
        if not widgets or not coupes:
            continue
        widget, coupe = widgets[-1], coupes[-1]
        try:




            if hasattr(widget, "SetPlaceFactor"):
                widget.SetPlaceFactor(1.0)
            widget.PlaceWidget(bounds)
            rep = widget.GetPlaneProperty()
            rep.SetOpacity(0.15)
            if hasattr(widget, "GetOutlineProperty"):
                widget.GetOutlineProperty().SetOpacity(0.0)
        except (AttributeError, TypeError):
            pass

        def _actualiser(objet, _event, i=index, sortie=coupe):
            try:
                options.plans[i].normale = tuple(
                    float(v) for v in objet.GetNormal())
                options.plans[i].origine = tuple(
                    float(v) for v in objet.GetOrigin())
            except AttributeError:
                return
            _mettre_a_jour_superpositions_coupe(
                plotter, i, options.plans[i], sortie,
                grille_vectorielle, nom_scalaire, options,
                longueur_reference, echelle_log=echelle_log, clim=clim,
                cmap=cmap, grille_scalaire=grille_scalaire,
                options_rendu=options_rendu)
            if hasattr(plotter, "render"):
                plotter.render()

        try:
            widget.AddObserver("InteractionEvent", _actualiser)
        except AttributeError:
            pass
        _mettre_a_jour_superpositions_coupe(
            plotter, index, plan, coupe, grille_vectorielle,
            nom_scalaire, options, longueur_reference,
            echelle_log=echelle_log, clim=clim, cmap=cmap,
            grille_scalaire=grille_scalaire, options_rendu=options_rendu)


def graines_lignes_champ(grille_vectorielle, options: OptionsRendu3D,
                         nom: str = "champ") -> pv.PolyData:
    graines_opts = options.graines or OptionsGraines3D()
    bounds = grille_vectorielle.bounds
    etendues = np.array([
        bounds[1] - bounds[0], bounds[3] - bounds[2],
        bounds[5] - bounds[4]], dtype=float)
    longueur_reference = float(np.max(etendues))
    mode = graines_opts.mode or "Automatique"
    densite = max(2, int(options.densite_lignes))

    if mode == "Plan":
        centre = tuple(float(v) for v in grille_vectorielle.center)
        normale = np.asarray(options.source_lignes.normale, dtype=float)
        norme = float(np.linalg.norm(normale))
        normale = (normale / norme if norme > 1e-14
                   else np.array([0.0, 0.0, 1.0]))
        taille = max(1e-12,
                     options.taille_source_lignes * longueur_reference)
        resolution = max(1, densite - 1)
        points = pv.Plane(
            center=centre, direction=normale,
            i_size=taille, j_size=taille,
            i_resolution=resolution, j_resolution=resolution).points
    elif mode == "Surface":
        surface = grille_vectorielle.extract_surface(
            algorithm="dataset_surface")
        centre = np.asarray(grille_vectorielle.center)
        points = np.asarray(surface.points)


        points = centre + (points - centre) * (1.0 - graines_opts.marge)
    elif mode == "Ligne":
        points = points_graines_ligne(
            bounds, densite=densite, marge=graines_opts.marge,
            axe=int(np.argmax(etendues)))
    else:
        points = points_graines_volumiques(
            bounds, densite=densite, marge=graines_opts.marge,
            jitter=graines_opts.jitter,
            graine_aleatoire=graines_opts.graine_aleatoire)


    try:
        echantillon = pv.PolyData(np.asarray(points, dtype=float)).sample(
            grille_vectorielle)
        garder = np.ones(len(points), dtype=bool)
        if "vtkValidPointMask" in echantillon.array_names:
            garder &= np.asarray(
                echantillon["vtkValidPointMask"], dtype=bool)
        if nom in echantillon.array_names:
            mag = np.linalg.norm(
                np.asarray(echantillon[nom], dtype=float), axis=1)
            if np.any(garder) and mag[garder].size:
                seuil = graines_opts.seuil_champ * float(
                    np.percentile(mag[garder], 98.0))
                garder &= mag > seuil
        if np.any(garder):
            points = np.asarray(points)[garder]
    except (KeyError, RuntimeError, TypeError, ValueError):
        points = np.asarray(points)
    points = sous_echantillonner(
        np.asarray(points, dtype=float), graines_opts.max_graines)
    return pv.PolyData(points)


def _ajouter_lignes_champ(
        plotter, field, grille_scalaire, grille_vectorielle,
        nom_scalaire, cmap, clim, barre, options, echelle_log=False,
        afficher_barre=True):
    source = graines_lignes_champ(grille_vectorielle, options)
    if source.n_points == 0:
        return
    bounds = grille_vectorielle.bounds
    longueur_reference = float(max(
        bounds[1] - bounds[0], bounds[3] - bounds[2],
        bounds[5] - bounds[4]))
    try:
        lignes = construire_streamlines(
            field, grille_pt=grille_vectorielle, source=source)
        if lignes.n_points == 0:
            return
        if nom_scalaire not in lignes.array_names:
            lignes = lignes.sample(grille_scalaire)
        tubes = lignes.tube(
            radius=max(1e-12, options.rayon_tubes * longueur_reference),
            n_sides=10)
        plotter.add_mesh(
            tubes, scalars=nom_scalaire, cmap=cmap, clim=clim,
            log_scale=echelle_log,
            scalar_bar_args=barre, show_scalar_bar=bool(afficher_barre),
            line_width=2, lighting=False,
            name="lignes_champ_3d", render=False)
        if options.graines and options.graines.afficher_graines:
            plotter.add_mesh(
                source, color="#22c55e", point_size=6,
                render_points_as_spheres=True, show_scalar_bar=False,
                name="graines_lignes_3d", render=False)
    except (KeyError, RuntimeError, TypeError, ValueError):
        return


def dessiner(plotter, field, kind: str = "Carte scalaire",
             scalaire: str = "V", opacite: float = 1.0, aretes: bool = False,
             grille_axes: bool = True, plan_interactif: bool = False,
             libelle_champ: str = None,
             kappa_pondere: bool = False,
             selection_scalaire: str = "Scalaire principal",
             libelle_kappa: str = None,
             options_coupe: OptionsCoupe3D = None,
             options_rendu: OptionsRendu3D = None,
             calques: CalquesRendu3D = None,
             conserver_camera: bool = False,
             theme_sombre: bool = False) -> ScalaireAffiche3D:
    camera_avant = None
    if conserver_camera:
        try:
            camera_avant = plotter.camera_position
        except (AttributeError, RuntimeError):
            camera_avant = None
    plotter.clear()
    if hasattr(plotter, "clear_plane_widgets"):
        try:
            plotter.clear_plane_widgets()
        except Exception:
            pass
    if hasattr(plotter, "clear_box_widgets"):
        try:
            plotter.clear_box_widgets()
        except Exception:
            pass
    if hasattr(plotter, "clear_line_widgets"):
        try:
            plotter.clear_line_widgets()
        except Exception:
            pass
    options_rendu = options_rendu or OptionsRendu3D()

    ancien_plan = (kind == "Plan de coupe")
    if kind == "Intensité du champ":
        selection_scalaire = "Intensité du champ"
        kind = "Carte scalaire"
    elif ancien_plan:
        kind = "Carte scalaire"
        if plan_interactif:
            options_coupe = options_coupe or OptionsCoupe3D()
            options_coupe.active = True

    if calques is None:
        calques = calques_depuis_mode(
            "Plan de coupe" if ancien_plan and plan_interactif else kind)
        if options_coupe is not None and options_coupe.active:
            calques.coupe = True
    else:
        calques = calques.copy()
    if calques.volume:
        calques.volume = False
        calques.carte_scalaire = True
    afficher_coupe = bool(
        calques.coupe or (options_coupe and options_coupe.active))
    if afficher_coupe and options_coupe is None:
        options_coupe = OptionsCoupe3D(active=True)
    if options_coupe is not None:
        options_coupe.active = afficher_coupe

    besoin_vecteurs = (
        calques.fleches or calques.lignes_champ
        or bool(afficher_coupe and options_coupe
                and (options_coupe.vecteurs_projetes
                     or options_coupe.lignes_champ))
        or selection_scalaire in ("intensite", "Intensité du champ"))
    (grille, grille_scalaire, grille_vectorielle,
     nom_scalaire, valeurs_affichees,
     libelle_affiche) = _preparer_scalaire_3d(
        field, selection_scalaire, scalaire, libelle_champ,
        libelle_kappa, kappa_pondere, besoin_vecteurs=besoin_vecteurs)
    _preparer_zone_iso(field, grille_scalaire, grille_vectorielle)

    cmap, clim, echelle_log = _carte_couleurs(valeurs_affichees)
    barre = _args_barre(libelle_affiche, theme_sombre)
    notes_hud = []
    if echelle_log:
        notes_hud.append("Échelle couleur : LOG (bornes robustes 2-98 %)")
    if grille_vectorielle is not None:


        grille_vectorielle[nom_scalaire] = valeurs_affichees



    barre_prise = [False]

    def _barre_kwargs():
        if barre_prise[0]:
            return {"show_scalar_bar": False}
        barre_prise[0] = True
        return {"scalar_bar_args": barre, "show_scalar_bar": True}

    if ancien_plan and not plan_interactif:


        plotter.add_mesh(
            grille_scalaire, style="wireframe", color="gray", opacity=0.15)
        coupe = grille_scalaire.slice(
            normal=(1.0, 0.0, 0.0), origin=grille_scalaire.center)
        plotter.add_mesh(
            coupe, scalars=nom_scalaire, cmap=cmap, clim=clim,
            log_scale=echelle_log, scalar_bar_args=barre)
        barre_prise[0] = True
    else:

        enveloppe_contexte = (
            not calques.carte_scalaire and not calques.volume
            and (calques.iso_surfaces or calques.fleches
                 or calques.lignes_champ or afficher_coupe))
        if enveloppe_contexte:



            plotter.add_mesh(
                grille_scalaire, scalars=nom_scalaire, cmap=cmap,
                clim=clim, log_scale=echelle_log,
                style="wireframe" if calques.lignes_champ else "surface",
                opacity=0.08, show_scalar_bar=False,
                name="enveloppe_3d")

        if calques.carte_scalaire:







            opacite_effective = opacite
            if afficher_coupe and opacite > 0.35:
                opacite_effective = 0.35
                notes_hud.append("Coupe active : volume rendu translucide")
            elif calques.lignes_champ or calques.iso_surfaces \
                    or calques.fleches:
                if opacite > 0.35:
                    opacite_effective = 0.35
                    notes_hud.append(
                        "Calques combinés : carte rendue translucide")
            else:
                try:
                    bord = np.asarray(field.mesh.boundary_nodes())
                except AttributeError:
                    bord = np.empty(0, dtype=int)
                etendue_totale = float(np.ptp(valeurs_affichees))
                if (bord.size and opacite > 0.35 and etendue_totale > 0
                        and float(np.ptp(valeurs_affichees[bord]))
                        <= 0.05 * etendue_totale):
                    opacite_effective = 0.35
                    notes_hud.append(
                        "Surface extérieure uniforme : "
                        "volume rendu translucide")
            _ajouter_clip_boite(
                plotter, grille_scalaire, options_coupe,
                scalars=nom_scalaire, cmap=cmap, clim=clim,
                log_scale=echelle_log,
                opacity=opacite_effective, show_edges=aretes,
                name="carte_3d", **_barre_kwargs())

        if calques.volume:
            if np.ptp(valeurs_affichees) <= 1e-14 \
                    or not hasattr(plotter, "add_volume"):
                if not calques.carte_scalaire:
                    _ajouter_clip_boite(
                        plotter, grille_scalaire, options_coupe,
                        scalars=nom_scalaire, cmap=cmap, clim=clim,
                        log_scale=echelle_log,
                        opacity=min(0.35, opacite), name="carte_3d",
                        **_barre_kwargs())
            else:
                afficher = not barre_prise[0]
                _ajouter_volume(
                    plotter, grille_scalaire, nom_scalaire, cmap, clim,
                    courbe_opacite(options_rendu.courbe_volume, opacite),
                    barre, options_coupe, afficher_barre=afficher)
                barre_prise[0] = barre_prise[0] or afficher

        if calques.iso_surfaces:



            reference = float(np.max(np.abs(valeurs_affichees))) \
                if valeurs_affichees.size else 0.0
            contours = None
            if np.ptp(valeurs_affichees) > 1e-9 * max(reference, 1e-30):
                if echelle_log and clim and clim[0] > 0:
                    niveaux = niveaux_isosurfaces_geometriques(
                        clim[0], clim[1], options_rendu.nombre_isosurfaces,
                        options_rendu.fraction_iso_min,
                        options_rendu.fraction_iso_max)
                else:
                    niveaux = niveaux_isosurfaces(
                        valeurs_affichees, options_rendu.nombre_isosurfaces,
                        options_rendu.fraction_iso_min,
                        options_rendu.fraction_iso_max)
                if np.asarray(niveaux).size:
                    grille_iso = _exclure_objets_des_iso(grille_scalaire)
                    candidats = (grille_iso.contour(
                        isosurfaces=niveaux, scalars=nom_scalaire)
                        if grille_iso is not None else None)
                    if candidats is not None and candidats.n_points > 0:
                        contours = candidats
            if contours is None:
                if not (calques.carte_scalaire or calques.volume
                        or enveloppe_contexte):
                    _ajouter_clip_boite(
                        plotter, grille_scalaire, options_coupe,
                        scalars=nom_scalaire, cmap=cmap, clim=clim,
                        log_scale=echelle_log,
                        opacity=0.35, name="carte_3d", **_barre_kwargs())
            else:
                _ajouter_clip_boite(
                    plotter, contours, options_coupe,
                    scalars=nom_scalaire, cmap=cmap, clim=clim,
                    log_scale=echelle_log,
                    opacity=0.85 if calques.lignes_champ
                    or calques.fleches else 1.0,
                    name="isosurfaces_3d", **_barre_kwargs())

        if calques.fleches:
            fleches = construire_glyphes(
                field, grille_pt=grille_vectorielle,
                scalaire_couleur=valeurs_affichees,
                nom_scalaire=nom_scalaire,
                pas=max(1, int(options_rendu.pas_glyphes)),
                taille_relative=options_rendu.taille_glyphes,
                normaliser=True)
            _ajouter_clip_boite(
                plotter, fleches, options_coupe,
                scalars=nom_scalaire, cmap=cmap, clim=clim,
                log_scale=echelle_log,
                name="fleches_3d", **_barre_kwargs())

        if calques.lignes_champ:
            afficher = not barre_prise[0]
            _ajouter_lignes_champ(
                plotter, field, grille_scalaire, grille_vectorielle,
                nom_scalaire, cmap, clim, barre, options_rendu,
                echelle_log=echelle_log, afficher_barre=afficher)
            barre_prise[0] = barre_prise[0] or afficher

        if calques.maillage:
            plotter.add_mesh(
                grille, style="wireframe",
                color="#6b7a93" if theme_sombre else "#94a3b8",
                opacity=0.35, line_width=1, show_scalar_bar=False,
                name="maillage_3d")

    info_scalaire = ScalaireAffiche3D(
        points=np.asarray(grille_scalaire.points),
        valeurs=valeurs_affichees,
        libelle=libelle_affiche,
        grille=grille_scalaire,
        nom_tableau=nom_scalaire,
    )
    if afficher_coupe and options_coupe is not None:
        _ajouter_coupes(
            plotter, grille_scalaire, grille_vectorielle,
            nom_scalaire, cmap, clim, barre, options_coupe,
            afficher_barre=not barre_prise[0],
            echelle_log=echelle_log, options_rendu=options_rendu)
        if options_coupe.fond_scalaire:
            barre_prise[0] = True
    _dessiner_scene(
        plotter, field, grille, info_scalaire,
        note_echelle="\n".join(notes_hud),
        objets=calques.objets_scene, theme_sombre=theme_sombre)

    plotter.add_axes()
    if grille_axes:


        couleur_axes = "#9aa7bd" if theme_sombre else "#4b5563"
        try:
            plotter.show_grid(
                mesh=grille, xtitle="x (m)", ytitle="y (m)", ztitle="z (m)",
                color=couleur_axes)
        except TypeError:
            try:
                plotter.show_grid(
                    mesh=grille, xtitle="x (m)", ytitle="y (m)",
                    ztitle="z (m)")
            except TypeError:
                plotter.show_grid()
    if camera_avant is not None:
        plotter.camera_position = camera_avant
    else:
        try:
            plotter.reset_camera(bounds=grille.bounds)
        except TypeError:
            plotter.reset_camera()
    return info_scalaire
