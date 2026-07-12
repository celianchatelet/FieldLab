import numpy as np
import skfem

from fieldlab.fem3d import mesh_gmsh
from fieldlab.fem3d import obstacles as obs3d
from fieldlab.fem3d.field3d import Field3D
from fieldlab.fem3d.mesh import box_mesh, unit_cube_mesh
from fieldlab.fem3d.regime_variable import resoudre_regime_variable_3d
from fieldlab.fem3d.scene import (
    ItemGeometrie, Scene3D, item_depuis_obstacle, scene_cube,
)
from fieldlab.fem3d.transient import resoudre_transitoire_3d
from fieldlab.materials import MATERIAUX, kappa_pour_domaine


def environnement_vide(n: int = 20, refine: int = 0,
                       dimensions=(1.0, 1.0, 1.0),
                       materiau_ambiant="Air", domaine_nom="Electrostatique",
                       scene: Scene3D = None, obstacles=None, walls=None,
                       **_kwargs) -> Field3D:
    if scene is None:
        dimensions = np.asarray(dimensions, dtype=float)
        scene = Scene3D(
            float(np.max(dimensions)),
            ((0.0, 0.0, 0.0), tuple(dimensions)),
            materiau_ambiant=materiau_ambiant)
    if obstacles or walls:
        scene = Scene3D(
            scene.taille_m, scene.boite_domaine,
            items=(list(scene.items)
                   + [item_depuis_obstacle(o, i)
                      for i, o in enumerate(obstacles or [])]
                   + _items_parois_cube(walls, float(np.max(scene.dimensions)))),
            circuits=scene.circuits,
            materiau_ambiant=scene.materiau_ambiant,
            taille_maille_cao=scene.taille_maille_cao)
    dimensions = scene.dimensions
    if scene.a_geometrie_cao:
        mesh = mesh_gmsh.scene_cao_mesh(
            scene, taille_maille=scene.taille_maille_cao)
    else:
        mesh = box_mesh(n, dimensions, refine=refine)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene)
    obs3d.appliquer_items_scene(
        champ, scene, domaine_nom, appliquer_ambiant=True)
    _appliquer_parois_cube(champ, walls)
    return champ


def environnement_vide_electrostatique(**kwargs) -> Field3D:
    return environnement_vide(domaine_nom="Electrostatique", **kwargs)


def environnement_vide_thermique(**kwargs) -> Field3D:
    return environnement_vide(domaine_nom="Thermique", **kwargs)


def _item_paroi_cube(face: str, spec: tuple,
                      taille_m: float) -> ItemGeometrie:
    epaisseur = 0.01 * taille_m
    params = {"x0": 0.0, "x1": taille_m,
              "y0": 0.0, "y1": taille_m,
              "z0": 0.0, "z1": taille_m}
    cote_min, cote_max = {
        "gauche": ("x0", "x1"), "droite": ("x1", "x0"),
        "avant": ("y0", "y1"), "arriere": ("y1", "y0"),
        "bas": ("z0", "z1"), "haut": ("z1", "z0"),
    }[face]
    if face in ("gauche", "avant", "bas"):
        params[cote_max] = epaisseur
    else:
        params[cote_max] = taille_m - epaisseur

    kind = spec[0]
    if kind == "dirichlet":
        return ItemGeometrie(
            "boite", params, role="electrode", valeur=spec[1],
            label=f"Paroi {face} — valeur imposée")
    if kind == "robin":
        valeur = f"h={spec[1]:g} W/m².K, ambiant={spec[2]:g} °C"
    elif kind == "radiation":
        valeur = f"ε={spec[1]:g}, ambiant={spec[2]:g} °C"
    elif kind == "flux":
        valeur = f"q={spec[1]:g} W/m²"
    else:
        valeur = kind
    return ItemGeometrie(
        "boite", params, role="source", valeur=valeur,
        label=f"Paroi {face} — {kind}")


def _items_parois_cube(walls: dict, taille_m: float) -> list:
    return [_item_paroi_cube(face, spec, taille_m)
            for face, spec in (walls or {}).items()
            if spec and spec[0] != "neumann"]


def _appliquer_parois_cube(champ: Field3D, walls: dict) -> None:
    x, y, z = champ.basis.doflocs
    minimum = champ.mesh.p.min(axis=1)
    maximum = champ.mesh.p.max(axis=1)
    coord_par_face = {
        "gauche": (x, minimum[0]), "droite": (x, maximum[0]),
        "avant": (y, minimum[1]), "arriere": (y, maximum[1]),
        "bas": (z, minimum[2]), "haut": (z, maximum[2]),
    }
    for face, spec in (walls or {}).items():
        if spec[0] == "dirichlet":
            coord, valeur_face = coord_par_face[face]
            masque = np.isclose(coord, valeur_face)
            champ.V[masque] = spec[1]
            champ.fixed_mask[masque] = True
            champ.walls[face] = ("neumann",)
        else:
            champ.walls[face] = spec


def cube_personnalise(n: int = 20, refine: int = 0, walls: dict = None,
                       obstacles: list = None,
                       taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    items = [item_depuis_obstacle(o, i)
             for i, o in enumerate(obstacles or [])]
    items.extend(_items_parois_cube(walls, taille_m))
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    obs3d.appliquer_obstacles(champ, obstacles)
    _appliquer_parois_cube(champ, walls)
    return champ


def cube_chauffe(n: int = 20, refine: int = 0, t_chaud: float = 100.0,
                  t_froid: float = 0.0,
                  taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    x, y, z = basis.doflocs
    zmin, zmax = float(z.min()), float(z.max())
    fixed = np.isclose(z, zmin) | np.isclose(z, zmax)
    V = np.where(np.isclose(z, zmax), t_chaud, t_froid)
    epaisseur = 0.01 * taille_m
    items = [
        ItemGeometrie(
            "boite", {"x0": 0.0, "y0": 0.0, "z0": zmin,
                       "x1": taille_m, "y1": taille_m,
                       "z1": zmin + epaisseur},
            role="electrode", valeur=t_froid, label="Face basse imposée",
            couleur="#2563eb"),
        ItemGeometrie(
            "boite", {"x0": 0.0, "y0": 0.0,
                       "z0": zmax - epaisseur, "x1": taille_m,
                       "y1": taille_m, "z1": zmax},
            role="electrode", valeur=t_chaud, label="Face haute imposée",
            couleur="#dc2626"),
    ]
    return Field3D(
        mesh, basis, V, fixed,
        scene=scene_cube(taille_m, items=items))


def cube_convection(n: int = 20, refine: int = 0, h: float = 10.0,
                     t_inf_bas: float = 20.0, t_inf_haut: float = 80.0,
                     taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    V = np.zeros(basis.N)
    fixed = np.zeros(basis.N, dtype=bool)
    walls = {
        "gauche": ("neumann",), "droite": ("neumann",),
        "avant": ("neumann",), "arriere": ("neumann",),
        "bas": ("robin", h, t_inf_bas),
        "haut": ("robin", h, t_inf_haut),
    }
    items = _items_parois_cube(walls, taille_m)
    return Field3D(
        mesh, basis, V, fixed, walls=walls,
        scene=scene_cube(taille_m, items=items))


def cube_avec_sphere(n: int = 20, refine: int = 0, materiau: str = "Cuivre",
                      t_chaud: float = 100.0, t_froid: float = 0.0,
                      rayon: float = 0.25,
                      taille_m: float = 1.0) -> Field3D:
    champ = cube_chauffe(
        n=n, refine=refine, t_chaud=t_chaud, t_froid=t_froid,
        taille_m=taille_m)
    kappa_val = kappa_pour_domaine(MATERIAUX[materiau], "Thermique")
    centre = taille_m / 2.0
    rayon_m = rayon * taille_m
    obs3d.sphere(
        champ, centre, centre, centre, rayon_m, ("materiau", kappa_val))
    champ.scene.items.append(ItemGeometrie(
        "sphere", {"cx": centre, "cy": centre, "cz": centre,
                   "r": rayon_m},
        role="materiau", materiau=materiau,
        label=f"Sphere {materiau}"))
    return champ


def condensateur_3d(n: int = 20, refine: int = 0, v: float = 10.0,
                     x0: float = 0.3, x1: float = 0.7,
                     epaisseur: float = 0.04,
                     taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    plaque_pos = {"x0": x0 * p, "y0": 0.15 * p, "z0": 0.15 * p,
                  "x1": (x0 + epaisseur) * p,
                  "y1": 0.85 * p, "z1": 0.85 * p}
    plaque_neg = {"x0": (x1 - epaisseur) * p,
                  "y0": 0.15 * p, "z0": 0.15 * p, "x1": x1 * p,
                  "y1": 0.85 * p, "z1": 0.85 * p}
    items = [
        ItemGeometrie(
            "boite", plaque_pos, role="electrode", valeur=v,
            label="Electrode positive"),
        ItemGeometrie(
            "boite", plaque_neg, role="electrode", valeur=-v,
            label="Electrode negative"),
    ]
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    obs3d.boite(champ, bc=("dirichlet", v), **plaque_pos)
    obs3d.boite(champ, bc=("dirichlet", -v), **plaque_neg)
    return champ


def coquille_spherique(n: int = 16, r_int: float = 0.3, r_ext: float = 1.0,
                        t_int: float = 100.0, t_ext: float = 0.0,
                        taille_m: float = None) -> Field3D:
    if taille_m is None:
        r_int_m, r_ext_m = r_int, r_ext
        taille_scene = 2.0 * r_ext
    else:
        facteur = float(taille_m) / (2.0 * r_ext)
        r_int_m, r_ext_m = r_int * facteur, r_ext * facteur
        taille_scene = float(taille_m)
    taille_maille = 1.2 * r_ext_m / n
    mesh = mesh_gmsh.sphere_creuse_mesh(
        r_int_m, r_ext_m, taille_maille=taille_maille)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    inner = mesh_gmsh.noeuds_bord_pres_du_rayon(basis, r_int_m, [r_ext_m])
    outer = mesh_gmsh.noeuds_bord_pres_du_rayon(basis, r_ext_m, [r_int_m])
    fixed = np.zeros(basis.N, dtype=bool)
    V = np.zeros(basis.N)
    fixed[inner] = True
    V[inner] = t_int
    fixed[outer] = True
    V[outer] = t_ext
    items = [
        ItemGeometrie(
            "sphere", {"cx": 0.0, "cy": 0.0, "cz": 0.0,
                       "r": r_int_m},
            role="electrode", valeur=t_int, label="Surface interieure",
            couleur="#dc2626"),
        ItemGeometrie(
            "sphere", {"cx": 0.0, "cy": 0.0, "cz": 0.0,
                       "r": r_ext_m},
            role="electrode", valeur=t_ext, label="Surface exterieure",
            couleur="#2563eb"),
    ]
    scene = Scene3D(
        taille_scene,
        ((-r_ext_m, -r_ext_m, -r_ext_m),
         (r_ext_m, r_ext_m, r_ext_m)),
        items=items)
    return Field3D(mesh, basis, V, fixed, scene=scene)


def sphere_chauffee(n: int = 16, r: float = 1.0, q: float = 12.0,
                    taille_m: float = None) -> Field3D:
    r_m = r if taille_m is None else float(taille_m) / 2.0
    taille_scene = 2.0 * r_m
    taille_maille = 1.2 * r_m / n
    mesh = mesh_gmsh.sphere_pleine_mesh(r_m, taille_maille=taille_maille)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    fixed = np.zeros(basis.N, dtype=bool)
    V = np.zeros(basis.N)
    fixed[mesh.boundary_nodes()] = True
    source = np.full(basis.N, q)
    item = ItemGeometrie(
        "sphere", {"cx": 0.0, "cy": 0.0, "cz": 0.0, "r": r_m},
        role="source", q=q, label="Source volumique")
    scene = Scene3D(
        taille_scene,
        ((-r_m, -r_m, -r_m), (r_m, r_m, r_m)),
        items=[item])
    return Field3D(mesh, basis, V, fixed, source=source, scene=scene)









def dipole_3d(n: int = 16, refine: int = 0, v: float = 10.0,
              taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    rayon = 0.08 * p
    items = [
        ItemGeometrie(
            "sphere", {"cx": 0.35 * p, "cy": 0.5 * p, "cz": 0.5 * p,
                       "r": rayon},
            role="electrode", valeur=v, label="Sphère +V"),
        ItemGeometrie(
            "sphere", {"cx": 0.65 * p, "cy": 0.5 * p, "cz": 0.5 * p,
                       "r": rayon},
            role="electrode", valeur=-v, label="Sphère −V"),
    ]
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    obs3d.sphere(champ, 0.35 * p, 0.5 * p, 0.5 * p, rayon, ("dirichlet", v))
    obs3d.sphere(champ, 0.65 * p, 0.5 * p, 0.5 * p, rayon, ("dirichlet", -v))
    return champ


def ligne_bifilaire_3d(n: int = 16, refine: int = 0, v: float = 10.0,
                       taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    rayon = 0.06 * p
    params = []
    for cx, valeur, label in ((0.38 * p, v, "Conducteur +V"),
                              (0.62 * p, -v, "Conducteur −V")):
        params.append(ItemGeometrie(
            "cylindre", {"cx": cx, "cy": 0.5 * p, "cz": 0.5 * p,
                         "r": rayon, "longueur": p, "axe": "z"},
            role="electrode", valeur=valeur, label=label))
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=params))
    obs3d.cylindre(champ, 0.38 * p, 0.5 * p, 0.5 * p, rayon, p,
                   ("dirichlet", v), axe="z")
    obs3d.cylindre(champ, 0.62 * p, 0.5 * p, 0.5 * p, rayon, p,
                   ("dirichlet", -v), axe="z")
    return champ


def cable_coaxial_3d(n: int = 16, refine: int = 0, v: float = 10.0,
                     taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    r_ame, r_blindage = 0.10 * p, 0.40 * p
    items = [
        ItemGeometrie(
            "cylindre", {"cx": 0.5 * p, "cy": 0.5 * p, "cz": 0.5 * p,
                         "r": r_ame, "longueur": p, "axe": "z"},
            role="electrode", valeur=v, label="Âme (+V)"),
        ItemGeometrie(
            "cylindre", {"cx": 0.5 * p, "cy": 0.5 * p, "cz": 0.5 * p,
                         "r": r_blindage, "longueur": p, "axe": "z"},
            role="electrode", valeur=0.0,
            label="Blindage (masse, au-delà)", couleur="#64748b"),
    ]
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    x, y, _z = basis.doflocs
    rayon_xy = np.hypot(x - 0.5 * p, y - 0.5 * p)
    exterieur = rayon_xy >= r_blindage
    champ.V[exterieur] = 0.0
    champ.fixed_mask[exterieur] = True
    obs3d.cylindre(champ, 0.5 * p, 0.5 * p, 0.5 * p, r_ame, p,
                   ("dirichlet", v), axe="z")
    return champ


def cage_faraday_3d(n: int = 16, refine: int = 0, v: float = 10.0,
                    taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    plaque_pos = {"x0": 0.06 * p, "x1": 0.10 * p, "y0": 0.10 * p,
                  "y1": 0.90 * p, "z0": 0.10 * p, "z1": 0.90 * p}
    plaque_neg = {"x0": 0.90 * p, "x1": 0.94 * p, "y0": 0.10 * p,
                  "y1": 0.90 * p, "z0": 0.10 * p, "z1": 0.90 * p}
    demi_int, demi_ext = 0.16 * p, 0.22 * p
    items = [
        ItemGeometrie("boite", plaque_pos, role="electrode", valeur=v,
                      label="Plaque +V"),
        ItemGeometrie("boite", plaque_neg, role="electrode", valeur=-v,
                      label="Plaque −V"),
        ItemGeometrie(
            "boite", {"cx": 0.5 * p, "cy": 0.5 * p, "cz": 0.5 * p,
                      "lx": 2 * demi_ext, "ly": 2 * demi_ext,
                      "lz": 2 * demi_ext},
            role="electrode", valeur=0.0, label="Cage (creuse, 0 V)",
            couleur="#64748b"),
    ]
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    obs3d.boite(champ, bc=("dirichlet", v), **plaque_pos)
    obs3d.boite(champ, bc=("dirichlet", -v), **plaque_neg)
    x, y, z = basis.doflocs
    ecart_max = np.maximum.reduce([
        np.abs(x - 0.5 * p), np.abs(y - 0.5 * p), np.abs(z - 0.5 * p)])
    coquille = (ecart_max >= demi_int) & (ecart_max <= demi_ext)
    champ.V[coquille] = 0.0
    champ.fixed_mask[coquille] = True
    return champ


def pointe_plan_3d(n: int = 16, refine: int = 0, v: float = 10.0,
                   taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    rayon = 0.05 * p
    corps = {"cx": 0.30 * p, "cy": 0.5 * p, "cz": 0.5 * p,
             "r": rayon, "longueur": 0.36 * p, "axe": "x"}
    bout = {"cx": 0.48 * p, "cy": 0.5 * p, "cz": 0.5 * p, "r": 0.055 * p}
    plaque = {"x0": 0.84 * p, "x1": 0.88 * p, "y0": 0.10 * p,
              "y1": 0.90 * p, "z0": 0.10 * p, "z1": 0.90 * p}
    items = [
        ItemGeometrie("cylindre", corps, role="electrode", valeur=v,
                      label="Pointe (+V)"),
        ItemGeometrie("sphere", bout, role="electrode", valeur=v,
                      label="Bout de la pointe"),
        ItemGeometrie("boite", plaque, role="electrode", valeur=0.0,
                      label="Plan (0 V)", couleur="#2563eb"),
    ]
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    obs3d.cylindre(champ, corps["cx"], corps["cy"], corps["cz"],
                   corps["r"], corps["longueur"], ("dirichlet", v), axe="x")
    obs3d.sphere(champ, bout["cx"], bout["cy"], bout["cz"], bout["r"],
                 ("dirichlet", v))
    obs3d.boite(champ, bc=("dirichlet", 0.0), **plaque)
    return champ


def tuyau_chaud_3d(n: int = 16, refine: int = 0, t_chaud: float = 100.0,
                   taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    rayon = 0.12 * p
    walls = {f: ("dirichlet", 0.0) for f in (
        "gauche", "droite", "avant", "arriere", "bas", "haut")}
    items = [ItemGeometrie(
        "cylindre", {"cx": 0.5 * p, "cy": 0.5 * p, "cz": 0.5 * p,
                     "r": rayon, "longueur": p, "axe": "z"},
        role="electrode", valeur=t_chaud, label="Tuyau chaud")]
    items.extend(_items_parois_cube(walls, taille_m))
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    _appliquer_parois_cube(champ, walls)
    obs3d.cylindre(champ, 0.5 * p, 0.5 * p, 0.5 * p, rayon, p,
                   ("dirichlet", t_chaud), axe="z")
    return champ


def echangeur_3d(n: int = 16, refine: int = 0, t_chaud: float = 100.0,
                 taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    rayon = 0.18 * p
    walls = {"gauche": ("dirichlet", t_chaud), "droite": ("dirichlet", 0.0),
             "avant": ("neumann",), "arriere": ("neumann",),
             "bas": ("neumann",), "haut": ("neumann",)}
    items = [ItemGeometrie(
        "sphere", {"cx": 0.5 * p, "cy": 0.5 * p, "cz": 0.5 * p, "r": rayon},
        role="isolant", label="Obstacle isolant")]
    items.extend(_items_parois_cube(walls, taille_m))
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    _appliquer_parois_cube(champ, walls)
    obs3d.sphere(champ, 0.5 * p, 0.5 * p, 0.5 * p, rayon, ("isolant",))
    return champ


def pont_thermique_3d(n: int = 16, refine: int = 0, t_chaud: float = 100.0,
                      taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    walls = {"gauche": ("dirichlet", t_chaud), "droite": ("dirichlet", 0.0),
             "avant": ("neumann",), "arriere": ("neumann",),
             "bas": ("neumann",), "haut": ("neumann",)}
    dalle_basse = {"x0": 0.46 * p, "x1": 0.54 * p, "y0": 0.0,
                   "y1": p, "z0": 0.0, "z1": 0.42 * p}
    dalle_haute = {"x0": 0.46 * p, "x1": 0.54 * p, "y0": 0.0,
                   "y1": p, "z0": 0.58 * p, "z1": p}
    items = [
        ItemGeometrie("boite", dalle_basse, role="isolant",
                      label="Paroi isolante (bas)"),
        ItemGeometrie("boite", dalle_haute, role="isolant",
                      label="Paroi isolante (haut)"),
    ]
    items.extend(_items_parois_cube(walls, taille_m))
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    _appliquer_parois_cube(champ, walls)
    obs3d.boite(champ, bc=("isolant",), **dalle_basse)
    obs3d.boite(champ, bc=("isolant",), **dalle_haute)
    return champ


def processeur_3d(n: int = 16, refine: int = 0, t_chaud: float = 100.0,
                  taille_m: float = 1.0) -> Field3D:
    mesh = unit_cube_mesh(n, refine=refine, taille_m=taille_m)
    basis = skfem.Basis(mesh, skfem.ElementTetP1())
    p = taille_m
    demi = 0.09 * p
    walls = {f: ("dirichlet", 0.0) for f in (
        "gauche", "droite", "avant", "arriere", "bas", "haut")}
    items = []
    blocs = []
    for i, (cx, cy) in enumerate(
            ((0.29, 0.29), (0.71, 0.29), (0.29, 0.71), (0.71, 0.71)), 1):
        bloc = {"x0": cx * p - demi, "x1": cx * p + demi,
                "y0": cy * p - demi, "y1": cy * p + demi,
                "z0": 0.5 * p - demi, "z1": 0.5 * p + demi}
        blocs.append(bloc)
        items.append(ItemGeometrie(
            "boite", bloc, role="electrode", valeur=t_chaud,
            label=f"Bloc chaud {i}"))
    items.extend(_items_parois_cube(walls, taille_m))
    champ = Field3D(
        mesh, basis, np.zeros(basis.N), np.zeros(basis.N, dtype=bool),
        scene=scene_cube(taille_m, items=items))
    _appliquer_parois_cube(champ, walls)
    for bloc in blocs:
        obs3d.boite(champ, bc=("dirichlet", t_chaud), **bloc)
    return champ





def cube_chauffe_transitoire(n: int = 16, T_initiale: float = 0.0, dt: float = 0.05,
                              duree: float = 3.0, n_images: int = 30,
                              taille_m: float = 1.0, annule=None):
    champ0 = cube_chauffe(n=n, taille_m=taille_m)
    return resoudre_transitoire_3d(champ0, T_initiale=T_initiale, dt=dt,
                                    duree=duree, n_images=n_images,
                                    annule=annule)


def cube_regime_variable(n: int = 16, amplitude: float = 100.0, forme: str = "Sinusoidale",
                          frequence: float = 0.5, duree: float = 2.0,
                          n_images: int = 40, taille_m: float = 1.0,
                          annule=None):
    champ0 = cube_chauffe(
        n=n, t_chaud=0.0, t_froid=0.0, taille_m=taille_m)
    champ0.scene.items[1].label = "Face haute — amplitude variable"
    champ0.scene.items[1].valeur = None
    x, y, z = champ0.basis.doflocs
    noeuds_haut = np.where(np.isclose(z, z.max()))[0]
    return resoudre_regime_variable_3d(champ0, noeuds_haut, valeur_pic=amplitude,
                                        forme=forme, frequence=frequence,
                                        duree=duree, n_images=n_images,
                                        annule=annule)







cube_chauffe_transitoire.constructible_hors_thread_principal = True
cube_regime_variable.constructible_hors_thread_principal = True
