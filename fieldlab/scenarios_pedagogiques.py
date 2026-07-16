"""Descriptions et réglages SI des scénarios prêts pour un cours."""

from fieldlab.i18n import langue_courante

DESCRIPTIONS = {
    "Condensateur plan": (
        "Deux armatures parallèles montrent un champ presque uniforme et V = E·d."),
    "Dipole (deux disques)": (
        "Deux électrodes opposées visualisent les équipotentielles d'un dipôle 2D."),
    "Cage de Faraday": (
        "Une enceinte conductrice au potentiel nul protège sa cavité du champ extérieur."),
    "Pointe - plan (effet de pointe)": (
        "La courbure élevée de la pointe concentre le champ électrique."),
    "Condensateur avec diélectrique partiel": (
        "Une plaque de verre dévie les lignes et modifie localement l'intensité de E."),
    "Fil unique": (
        "La coupe d'un fil infini vérifie B(r) = μ₀I/(2πr)."),
    "Deux fils (opposes)": (
        "Deux courants opposés montrent la superposition des champs magnétiques."),
    "Deux fils (meme sens)": (
        "Deux courants parallèles de même sens renforcent le champ à l'extérieur."),
    "Boucle de courant (dipole)": (
        "La coupe d'une spire fait apparaître un champ de type dipolaire."),
    "Solenoide (coupe)": (
        "Deux nappes de courant opposées créent un champ presque uniforme à l'intérieur."),
    "Bobines de Helmholtz (champ uniforme)": (
        "Deux bobines espacées de leur rayon produisent une zone centrale très uniforme."),
    "Mur composite (verre + plastique)": (
        "Deux couches en série montrent la rupture de pente liée aux conductivités."),
    "Ailette de refroidissement": (
        "Une ailette d'aluminium évacue la chaleur d'une base chaude vers l'air."),
    "Trempe (objet chaud dans l'eau)": (
        "Un objet de cuivre initialement chaud se refroidit par conduction dans l'eau."),
    "Pont thermique": (
        "Une zone très conductrice court-circuite localement l'isolation du mur."),
    "Plancher chauffant": (
        "Une source répartie sous le sol diffuse la chaleur vers une pièce plus froide."),
    "Tuyau chaud (enceinte froide)": (
        "Un cylindre maintenu chaud crée un front de diffusion radial dans le milieu."),
}

DESCRIPTIONS_EN = {
    "Condensateur plan":
        "Two parallel plates show an almost uniform field and V = E·d.",
    "Dipole (deux disques)":
        "Two opposite electrodes reveal the equipotentials of a 2D dipole.",
    "Cage de Faraday":
        "A grounded conducting enclosure shields its cavity from the external field.",
    "Pointe - plan (effet de pointe)":
        "The sharp tip's high curvature concentrates the electric field.",
    "Condensateur avec diélectrique partiel":
        "A glass slab bends the lines and locally changes the magnitude of E.",
    "Fil unique": "The cross-section of an infinite wire verifies B(r) = μ₀I/(2πr).",
    "Deux fils (opposes)":
        "Two opposite currents demonstrate superposition of magnetic fields.",
    "Deux fils (meme sens)":
        "Two parallel currents in the same direction reinforce the outer field.",
    "Boucle de courant (dipole)":
        "A current-loop cross-section produces a dipole-like field.",
    "Solenoide (coupe)":
        "Two opposite current sheets create an almost uniform inner field.",
    "Bobines de Helmholtz (champ uniforme)":
        "Two coils separated by their radius create a very uniform central region.",
    "Mur composite (verre + plastique)":
        "Two layers in series show the slope change caused by conductivity.",
    "Ailette de refroidissement":
        "An aluminum fin carries heat from a hot base to the surrounding air.",
    "Trempe (objet chaud dans l'eau)":
        "An initially hot copper object cools by conduction in water.",
    "Pont thermique":
        "A highly conductive region locally bypasses the wall insulation.",
    "Plancher chauffant":
        "A distributed source below the floor diffuses heat into a cooler room.",
    "Tuyau chaud (enceinte froide)":
        "A hot cylinder creates a radial diffusion front in the medium.",
}


PRESETS_2D = {
    "Electrostatique": {
        "Condensateur plan": {"taille": 0.20, "valeur": 100.0,
                               "viz": "Lignes de champ"},
        "Dipole (deux disques)": {"taille": 0.30, "valeur": 100.0,
                                   "viz": "Lignes de champ"},
        "Cage de Faraday": {"taille": 0.50, "valeur": 1000.0,
                             "viz": "Intensité du champ"},
        "Pointe - plan (effet de pointe)": {
            "taille": 0.20, "valeur": 5000.0,
            "viz": "Intensité du champ"},
        "Condensateur avec diélectrique partiel": {
            "taille": 0.10, "valeur": 100.0,
            "environnement": "Air (laboratoire)",
            "viz": "Lignes de champ"},
    },
    "Magnetostatique": {
        "Fil unique": {"taille": 0.20, "valeur": 16000.0,
                        "viz": "Intensité du champ"},
        "Deux fils (opposes)": {"taille": 0.20, "valeur": 16000.0,
                                "viz": "Lignes de champ"},
        "Deux fils (meme sens)": {"taille": 0.20, "valeur": 16000.0,
                                  "viz": "Lignes de champ"},
        "Boucle de courant (dipole)": {"taille": 0.20, "valeur": 40000.0,
                                        "viz": "Lignes de champ"},
        "Solenoide (coupe)": {"taille": 0.30, "valeur": 100000.0,
                               "viz": "Intensité du champ"},
    },
    "Thermique": {
        "Mur composite (verre + plastique)": {
            "taille": 0.20, "valeur": 80.0,
            "environnement": "Air (laboratoire)",
            "viz": "Carte scalaire"},
        "Ailette de refroidissement": {
            "taille": 0.20, "valeur": 100.0,
            "environnement": "Air (laboratoire)",
            "viz": "Iso-valeurs"},
        "Trempe (objet chaud dans l'eau)": {
            "taille": 0.05, "valeur": 80.0, "T_initiale": 15.0,
            "environnement": "Eau", "regime": "Transitoire",
            "duree": 2700.0, "vitesse_lecture": 1000,
            "viz": "Carte scalaire"},
        "Pont thermique": {
            "taille": 0.30, "valeur": 30.0,
            "environnement": "Air (laboratoire)",
            "viz": "Intensité du champ"},
        "Plancher chauffant": {
            "taille": 3.0, "valeur": 35.0,
            "environnement": "Air (laboratoire)",
            "viz": "Iso-valeurs"},
        "Tuyau chaud (enceinte froide)": {
            "taille": 0.20, "valeur": 80.0, "T_initiale": 15.0,
            "environnement": "Eau", "regime": "Transitoire",
            "vitesse_lecture": 1000, "viz": "Carte scalaire"},
    },
}


def description_scenario(nom: str) -> str:
    if langue_courante() == "en":
        return DESCRIPTIONS_EN.get(
            nom, "Preset scenario with physical values ready to simulate.")
    return DESCRIPTIONS.get(
        nom, "Scénario prédéfini avec des valeurs physiques prêtes à simuler.")


def preset_2d(domaine_nom: str, scenario: str) -> dict:
    return dict(PRESETS_2D.get(domaine_nom, {}).get(scenario, {}))
