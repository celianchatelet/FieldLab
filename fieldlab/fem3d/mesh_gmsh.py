import math
import os
from pathlib import Path
import tempfile

import gmsh
import meshio
import numpy as np
import skfem
from skfem.io.meshio import from_meshio


class ErreurMaillage3D(RuntimeError):
    pass


def _taille_adaptee(taille_maille, diagonale: float) -> float:
    if not np.isfinite(diagonale) or diagonale <= 0:
        raise ErreurMaillage3D("La géométrie CAO a une étendue nulle ou invalide.")
    if taille_maille is None:
        return diagonale / 22.0
    taille = float(taille_maille)
    if not np.isfinite(taille) or taille <= 0:
        raise ErreurMaillage3D("La taille de maille doit être strictement positive.")

    return min(max(taille, diagonale / 500.0), diagonale / 2.5)


def _verifier_tetraedres(mesh) -> None:
    if getattr(mesh, "t", np.empty((4, 0))).shape[1] == 0:
        raise ErreurMaillage3D("Gmsh n'a produit aucun tétraèdre.")
    p = np.asarray(mesh.p, dtype=float)
    t = np.asarray(mesh.t[:4], dtype=int)
    a = p[:, t[1]] - p[:, t[0]]
    b = p[:, t[2]] - p[:, t[0]]
    c = p[:, t[3]] - p[:, t[0]]
    six_volumes = np.abs(np.einsum("ij,ij->j", a, np.cross(b, c, axis=0)))


    echelle = max(float(np.ptp(p, axis=1).max()), np.finfo(float).eps)
    if np.any(~np.isfinite(six_volumes)) or np.any(six_volumes <= echelle ** 3 * 1e-14):
        raise ErreurMaillage3D(
            "Le maillage contient des tétraèdres dégénérés. Réparez la CAO "
            "ou augmentez la taille de maille.")


def _mesh_depuis_modele_gmsh(taille_maille: float) -> skfem.MeshTet:
    volumes = gmsh.model.getEntities(3)
    if not volumes:
        raise ErreurMaillage3D(
            "La géométrie ne contient aucun volume fermé à tétraédriser.")
    gmsh.option.setNumber("Mesh.MeshSizeMin", taille_maille / 4.0)
    gmsh.option.setNumber("Mesh.MeshSizeMax", taille_maille)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    try:
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.removeDuplicateNodes()
    except Exception as erreur:
        raise ErreurMaillage3D(
            "Gmsh n'a pas pu tétraédriser la géométrie : " + str(erreur)) from erreur
    types = gmsh.model.mesh.getElementTypes(dim=3)
    if not any(gmsh.model.mesh.getElementProperties(t)[0].lower().startswith("tetra")
               for t in types):
        raise ErreurMaillage3D("Gmsh n'a produit aucun élément tétraédrique.")
    with tempfile.NamedTemporaryFile(suffix=".msh", delete=False) as fichier:
        chemin = fichier.name
    try:
        gmsh.write(chemin)
        resultat = from_meshio(meshio.read(chemin))
        _verifier_tetraedres(resultat)
        return resultat
    except ErreurMaillage3D:
        raise
    except Exception as erreur:
        raise ErreurMaillage3D(
            "Le maillage Gmsh n'est pas convertible en maillage FieldLab : "
            + str(erreur)) from erreur
    finally:
        if os.path.exists(chemin):
            os.remove(chemin)


def _centre_et_dimensions(item):
    p = item.params
    if item.forme == "boite":
        if all(k in p for k in ("lx", "ly", "lz")):
            centre = np.array([p.get("cx", 0), p.get("cy", 0), p.get("cz", 0)], float)
            dimensions = np.array([p["lx"], p["ly"], p["lz"]], float)
        else:
            minimum = np.array([p["x0"], p["y0"], p["z0"]], float)
            maximum = np.array([p["x1"], p["y1"], p["z1"]], float)
            centre, dimensions = (minimum + maximum) / 2, maximum - minimum
        return centre, dimensions
    return np.array([p.get("cx", 0), p.get("cy", 0), p.get("cz", 0)], float), None


def _transformer_occ(dimtags, item, centre):
    rotation = np.radians(np.asarray(item.rotation, dtype=float))
    for angle, axe in zip(rotation, np.eye(3)):
        if not np.isclose(angle, 0.0):
            gmsh.model.occ.rotate(dimtags, *centre, *axe, float(angle))


def _ajouter_item_occ(item):
    p = item.params
    if item.forme == "boite":
        centre, dimensions = _centre_et_dimensions(item)
        if np.any(dimensions <= 0):
            raise ErreurMaillage3D(f"{item.label} a une dimension nulle ou négative.")
        tag = gmsh.model.occ.addBox(*(centre - dimensions / 2), *dimensions)
        dimtags = [(3, tag)]
    elif item.forme == "sphere":
        centre, _ = _centre_et_dimensions(item)
        rayon = float(p["r"])
        if rayon <= 0:
            raise ErreurMaillage3D(f"{item.label} a un rayon non positif.")
        dimtags = [(3, gmsh.model.occ.addSphere(*centre, rayon))]
    elif item.forme == "cylindre":
        centre, _ = _centre_et_dimensions(item)
        rayon, longueur = float(p["r"]), float(p["longueur"])
        if rayon <= 0 or longueur <= 0:
            raise ErreurMaillage3D(f"{item.label} a une dimension non positive.")
        axe = p.get("axe", "z")
        direction = {"x": (longueur, 0, 0), "y": (0, longueur, 0),
                     "z": (0, 0, longueur)}.get(axe)
        if direction is None:
            raise ErreurMaillage3D(f"Axe de cylindre inconnu : {axe!r}.")
        base = centre - np.asarray(direction) / 2
        dimtags = [(3, gmsh.model.occ.addCylinder(*base, *direction, rayon))]
    elif item.forme == "maillage_importe":
        chemin = Path(p.get("chemin", "")).expanduser()
        if not chemin.is_file():
            raise ErreurMaillage3D(f"Fichier importé introuvable : {chemin}")
        if chemin.suffix.lower() not in (".step", ".stp"):
            raise ErreurMaillage3D(
                "Les booléens OpenCASCADE acceptent les imports STEP. Un STL "
                "peut être tétraédrisé seul, mais pas converti fidèlement en solide CAO.")
        try:
            dimtags = [dt for dt in gmsh.model.occ.importShapes(str(chemin)) if dt[0] == 3]
        except Exception as erreur:
            raise ErreurMaillage3D(f"Import STEP impossible ({chemin.name}) : {erreur}") from erreur
        if not dimtags:
            raise ErreurMaillage3D(f"Le STEP {chemin.name} ne contient aucun solide fermé.")
        centre = np.asarray(p.get("centre", (0.0, 0.0, 0.0)), dtype=float)
        echelle = float(p.get("echelle", 1.0))
        if not np.isfinite(echelle) or echelle <= 0:
            raise ErreurMaillage3D("L'échelle d'import doit être positive.")
        if not np.isclose(echelle, 1.0):
            gmsh.model.occ.dilate(dimtags, 0, 0, 0, echelle, echelle, echelle)
        decalage = np.asarray(p.get("decalage", (0.0, 0.0, 0.0)), dtype=float)
        if np.any(decalage):
            gmsh.model.occ.translate(dimtags, *decalage)
    else:
        raise ErreurMaillage3D(f"Forme CAO inconnue : {item.forme!r}.")
    _transformer_occ(dimtags, item, centre)
    return dimtags


def _construire_occ(scene):
    items = scene.items_cao
    if not items:
        raise ErreurMaillage3D("La scène ne contient aucune opération CAO.")
    if items[0].operation_cao != "domaine":
        raise ErreurMaillage3D(
            "Le premier objet CAO doit porter l'opération « domaine ».")
    courant = _ajouter_item_occ(items[0])
    for item in items[1:]:
        if item.operation_cao == "domaine":
            raise ErreurMaillage3D("Une scène CAO ne peut avoir qu'un domaine initial.")
        outil = _ajouter_item_occ(item)
        try:
            if item.operation_cao == "union":
                courant, _ = gmsh.model.occ.fuse(courant, outil)
            elif item.operation_cao == "difference":
                courant, _ = gmsh.model.occ.cut(courant, outil)
            elif item.operation_cao == "intersection":
                courant, _ = gmsh.model.occ.intersect(courant, outil)
        except Exception as erreur:
            raise ErreurMaillage3D(
                f"Opération {item.operation_cao} impossible sur {item.label} : {erreur}") from erreur
        courant = [dt for dt in courant if dt[0] == 3]
        if not courant:
            raise ErreurMaillage3D(
                f"L'opération {item.operation_cao} avec {item.label} produit un domaine vide.")
    gmsh.model.occ.synchronize()
    return courant


def _construire_stl_seul(scene):
    items = scene.items_cao
    if len(items) != 1 or items[0].forme != "maillage_importe":
        return False
    chemin = Path(items[0].params.get("chemin", "")).expanduser()
    if chemin.suffix.lower() != ".stl":
        return False
    if not chemin.is_file():
        raise ErreurMaillage3D(f"Fichier STL introuvable : {chemin}")
    try:
        gmsh.merge(str(chemin))
        gmsh.model.mesh.classifySurfaces(math.radians(40), True, True, math.pi)
        gmsh.model.mesh.createGeometry()
        surfaces = [tag for _, tag in gmsh.model.getEntities(2)]
        if not surfaces:
            raise ErreurMaillage3D("Le STL ne contient aucune surface exploitable.")
        boucle = gmsh.model.geo.addSurfaceLoop(surfaces)
        gmsh.model.geo.addVolume([boucle])
        gmsh.model.geo.synchronize()
    except ErreurMaillage3D:
        raise
    except Exception as erreur:
        raise ErreurMaillage3D(
            "Le STL n'est pas une enveloppe fermée reparamétrable : " + str(erreur)) from erreur
    return True


def _diagonale_scene(scene) -> float:
    return float(np.linalg.norm(np.asarray(scene.dimensions, dtype=float)))


def scene_cao_mesh(scene, taille_maille=None) -> skfem.MeshTet:
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("fieldlab_scene_cao")
        if not _construire_stl_seul(scene):
            _construire_occ(scene)
        taille = _taille_adaptee(taille_maille, _diagonale_scene(scene))
        return _mesh_depuis_modele_gmsh(taille)
    except ErreurMaillage3D:
        raise
    except Exception as erreur:
        raise ErreurMaillage3D("Erreur Gmsh pendant la construction CAO : " + str(erreur)) from erreur
    finally:
        gmsh.finalize()


def surface_scene_cao(scene, taille_maille=None):
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("fieldlab_apercu_cao")
        if not _construire_stl_seul(scene):
            _construire_occ(scene)
        taille = _taille_adaptee(taille_maille, _diagonale_scene(scene))
        gmsh.option.setNumber("Mesh.MeshSizeMax", taille)
        gmsh.model.mesh.generate(2)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        points = np.asarray(coords, float).reshape(-1, 3)
        indices = {int(tag): i for i, tag in enumerate(tags)}
        triangles = []
        types, _, noeuds_par_type = gmsh.model.mesh.getElements(dim=2)
        for type_element, noeuds in zip(types, noeuds_par_type):
            nom, _, _, n_noeuds, *_ = gmsh.model.mesh.getElementProperties(type_element)
            if not nom.lower().startswith("triangle"):
                continue
            blocs = np.asarray(noeuds, dtype=np.int64).reshape(-1, n_noeuds)
            triangles.extend([[indices[int(tag)] for tag in bloc[:3]] for bloc in blocs])
        triangles = np.asarray(triangles, dtype=np.int64)
        if len(points) == 0 or len(triangles) == 0:
            raise ErreurMaillage3D("L'aperçu CAO ne contient aucun triangle.")
        return points, triangles
    except ErreurMaillage3D:
        raise
    except Exception as erreur:
        raise ErreurMaillage3D("Aperçu CAO impossible : " + str(erreur)) from erreur
    finally:
        gmsh.finalize()


def sphere_pleine_mesh(r: float = 1.0, taille_maille: float = 0.15) -> skfem.MeshTet:
    from fieldlab.fem3d.scene import ItemGeometrie, Scene3D
    scene = Scene3D(2 * r, ((-r, -r, -r), (r, r, r)), items=[
        ItemGeometrie("sphere", {"cx": 0, "cy": 0, "cz": 0, "r": r},
                       operation_cao="domaine")])
    return scene_cao_mesh(scene, taille_maille)


def sphere_creuse_mesh(r_int: float, r_ext: float,
                       taille_maille: float = 0.15) -> skfem.MeshTet:
    if not 0 < r_int < r_ext:
        raise ValueError("Il faut 0 < r_int < r_ext.")
    from fieldlab.fem3d.scene import ItemGeometrie, Scene3D
    scene = Scene3D(2 * r_ext, ((-r_ext,) * 3, (r_ext,) * 3), items=[
        ItemGeometrie("sphere", {"cx": 0, "cy": 0, "cz": 0, "r": r_ext},
                       operation_cao="domaine"),
        ItemGeometrie("sphere", {"cx": 0, "cy": 0, "cz": 0, "r": r_int},
                       operation_cao="difference"),
    ])
    return scene_cao_mesh(scene, taille_maille)


def noeuds_bord_pres_du_rayon(basis, rayon: float, autres_rayons,
                              centre=(0.0, 0.0, 0.0)) -> np.ndarray:
    x, y, z = basis.doflocs
    cx, cy, cz = centre
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)
    bnodes = basis.mesh.boundary_nodes()
    ecart = np.abs(r[bnodes] - rayon)
    for autre in autres_rayons:
        ecart_autre = np.abs(r[bnodes] - autre)
        garde = ecart <= ecart_autre
        bnodes, ecart = bnodes[garde], ecart[garde]
    return bnodes
