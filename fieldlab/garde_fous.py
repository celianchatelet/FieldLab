import numpy as np

from fieldlab.geometries import NOM_SCENE_LIBRE_2D

_METHODES_FD = ("Jacobi", "Gauss-Seidel", "SOR")
_PAROIS_FEM = ("robin", "radiation", "flux")


def estimation_cout_3d(n: int) -> tuple:
    n = int(n)
    noeuds = (n + 1) ** 3
    bande = (n + 1) ** 2
    memoire_mo = 2.0 * 8.0 * noeuds * bande / 1e6
    return noeuds, memoire_mo


def verifier_parametres(p: dict, domaine_nom: str) -> tuple:
    bloquants = []
    avertissements = []
    methode = p.get("method", "FEM (direct)")
    dimension = p.get("dimension", "2D")

    if dimension == "2D" and methode in _METHODES_FD:
        details = []
        if any((o.get("bc") or ("",))[0] == "materiau"
               for o in p.get("obstacles") or []):
            details.append("des objets « matériau » (conductivité/"
                           "permittivité réelle)")
        if abs(float(p.get("kappa_fond", 1.0)) - 1.0) > 1e-12:
            details.append("un milieu ambiant réel (environnement)")
        parois_fem = sorted({
            spec[0] for spec in (p.get("walls") or {}).values()
            if spec and spec[0] in _PAROIS_FEM})
        if parois_fem:
            details.append(
                "des parois " + "/".join(parois_fem)
                + " (convection/rayonnement/flux)")
        if details:
            bloquants.append(
                f"La méthode « {methode} » (différences finies) ignore "
                + ", ".join(details)
                + " : le résultat serait silencieusement faux.\n"
                "Choisissez « FEM (direct) » (méthode par défaut, section "
                "« Avancé — solveur numérique ») pour prendre ces éléments "
                "en compte.")

    if dimension == "2D":
        if (p.get("geom") == NOM_SCENE_LIBRE_2D
                and str(p.get("regime", "Stationnaire")) != "Transitoire"):
            ancrage_objet = any(
                (objet.get("bc") or (None,))[0] == "dirichlet"
                for objet in (p.get("obstacles") or []))
            ancrage_paroi = any(
                specification and specification[0] in (
                    "dirichlet", "robin", "radiation")
                for specification in (p.get("walls") or {}).values())
            if not (ancrage_objet or ancrage_paroi):
                bloquants.append(
                    "La scène libre 2D stationnaire n’a aucune valeur de "
                    "référence. Ajoutez un conducteur ou une température "
                    "imposée, ou choisissez une paroi Dirichlet, convection "
                    "ou rayonnement.")
        n = int(p.get("N", 0))
        raffinement = max(0, int(p.get("refine", 0) or 0))
        noeuds_effectifs = n * n * (4 ** raffinement)
        if noeuds_effectifs > 500_000 and methode.startswith("FEM"):
            avertissements.append(
                f"Maillage 2D élevé : N = {n}, raffinement = {raffinement}, "
                f"soit environ {noeuds_effectifs:,} nœuds FEM. Le calcul et "
                "la factorisation peuvent consommer beaucoup de mémoire.")
        elif n > 600:
            avertissements.append(
                f"Résolution 2D très élevée : N = {n} soit {n * n:,} "
                "nœuds. Le calcul itératif peut être long.")
    else:
        n3 = int(p.get("N_3d", 0))
        noeuds, memoire_mo = estimation_cout_3d(n3)
        if memoire_mo > 500.0:
            avertissements.append(
                f"Résolution 3D élevée : {n3} par arête soit "
                f"{noeuds:,} nœuds — factorisation directe estimée à "
                f"~{memoire_mo:,.0f} Mo de mémoire.")
        images = int(p.get("n_images_3d", p.get("n_images", 0)) or 0)
        if images > 200:
            avertissements.append(
                f"{images} images 3D seront conservées en mémoire pour le "
                "lecteur temporel : cela peut représenter plusieurs "
                "centaines de Mo.")
        scene = p.get("scene_3d")
        if scene is not None and getattr(scene, "a_geometrie_cao", False):
            h = float(getattr(scene, "taille_maille_cao", 0.0) or 0.0)
            if h > 0:
                cellules = float(np.prod(scene.dimensions)) / h ** 3
                if cellules > 1_000_000:
                    avertissements.append(
                        "La taille de maille CAO demandée peut produire plus "
                        f"d'un million de cellules (~{cellules:,.0f}).")

    if domaine_nom == "Thermique":
        parois = list((p.get("walls") or {}).values()) \
            + list((p.get("walls_3d") or {}).values())
        for spec in parois:
            if not spec:
                continue
            if spec[0] == "radiation":
                epsilon, ambiante = float(spec[1]), float(spec[2])
                if not 0.0 <= epsilon <= 1.0:
                    bloquants.append(
                        "L'émissivité d'une paroi radiative doit être comprise entre 0 et 1.")
                if ambiante < -273.15:
                    bloquants.append(
                        "La température radiative ambiante ne peut pas être sous le zéro absolu.")
            elif spec[0] == "robin" and float(spec[1]) < 0:
                bloquants.append(
                    "Le coefficient de convection h doit être positif ou nul.")
        regime_thermique = (p.get("regime_3d") if dimension == "3D"
                            else p.get("regime"))
        if str(regime_thermique or "").lower() == "transitoire":
            environnement = str(p.get("environnement", ""))
            rho_cp_fond = float(p.get("rho_cp_fond", 1.0))
            if (not environnement
                    or environnement.startswith("(aucun")
                    or np.isclose(rho_cp_fond, 1.0)):
                bloquants.append(
                    "Un milieu physique réel est obligatoire en thermique "
                    "transitoire. Sélectionnez Eau, Huile, Air ou un autre "
                    "environnement : ρ·cp = 1 est une normalisation et ne "
                    "représente pas une échelle de temps en secondes.")

    return bloquants, avertissements
