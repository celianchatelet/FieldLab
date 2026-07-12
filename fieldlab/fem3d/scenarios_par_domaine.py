from fieldlab.fem3d.scenarios import (
    cable_coaxial_3d, cage_faraday_3d, condensateur_3d, coquille_spherique,
    cube_avec_sphere, cube_chauffe,
    cube_convection, cube_regime_variable, dipole_3d,
    echangeur_3d, environnement_vide_electrostatique,
    environnement_vide_thermique, ligne_bifilaire_3d, pointe_plan_3d,
    pont_thermique_3d, processeur_3d, sphere_chauffee, tuyau_chaud_3d,
)













NOM_SCENE_LIBRE = "Scène libre (objets et parois personnalisés)"




SCENARIOS_3D_ELECTROSTATIQUE = {
    NOM_SCENE_LIBRE: environnement_vide_electrostatique,
    "Condensateur plan (deux plaques)": condensateur_3d,
    "Dipôle (deux sphères ±V)": dipole_3d,
    "Câble coaxial (âme + blindage)": cable_coaxial_3d,
    "Cage de Faraday": cage_faraday_3d,
    "Pointe - plan (effet de pointe)": pointe_plan_3d,
    "Ligne bifilaire (deux cylindres ±V)": ligne_bifilaire_3d,
    "Cube - deux electrodes (V)": lambda n, taille_m=1.0: cube_chauffe(
        n=n, t_chaud=10.0, t_froid=-10.0, taille_m=taille_m),
    "Cube - regime variable (electrode sinusoidale)": cube_regime_variable,
}

SCENARIOS_3D_THERMIQUE = {
    NOM_SCENE_LIBRE: environnement_vide_thermique,
    "Mur (gradient 1D) - cube chauffe": cube_chauffe,
    "Tuyau chaud (enceinte froide)": tuyau_chaud_3d,
    "Echangeur (obstacle isolant)": echangeur_3d,
    "Pont thermique": pont_thermique_3d,
    "Processeur (4 blocs chauds)": processeur_3d,
    "Cube convection (Robin, 6 faces)": cube_convection,
    "Cube + sphere cuivre (obstacle/materiau)": lambda n, taille_m=1.0: cube_avec_sphere(
        n=n, materiau="Cuivre", taille_m=taille_m),
    "Cube + sphere plastique (obstacle/materiau)": lambda n, taille_m=1.0: cube_avec_sphere(
        n=n, materiau="Plastique", taille_m=taille_m),
    "Coquille spherique (maillage gmsh)": coquille_spherique,
    "Sphere chauffee (maillage gmsh + source)": sphere_chauffee,
}
