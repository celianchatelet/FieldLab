"""Catalogue central FR/EN sans modifier les identifiants internes français.

Les widgets conservent leur texte source dans une propriété Qt. Les listes
déroulantes utilisent :class:`ComboBoxTraduit`, qui affiche la traduction mais
retourne toujours la valeur source à la logique métier.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton, QDialog, QDockWidget, QGroupBox, QLabel, QLineEdit,
    QMainWindow,
    QMenu, QTabWidget,
)


_langue = "fr"


EN = {
    "FieldLab — Simulateur multiphysique 2D/3D":
        "FieldLab — 2D/3D multiphysics simulator",
    "&Fichier": "&File", "&Affichage": "&View", "&Analyse": "&Analysis",
    "&Aide": "&Help", "Mode d'interface": "Interface mode",
    "Électricité": "Electricity", "Magnétisme": "Magnetism",
    "Thermique": "Thermal", "Contrôles": "Controls",
    "Paramètres": "Parameters", "Géométrie": "Geometry",
    "Environnement": "Environment", "Milieu physique 3D": "3D physical medium",
    "Régime": "Regime", "Stationnaire": "Steady state",
    "Transitoire": "Transient", "Variable": "Time-varying",
    "Dimension": "Dimension", "Scénario 3D": "3D scenario",
    "Visualisation": "Visualization", "Mode de rendu": "Rendering mode",
    "Grandeur affichée": "Displayed quantity", "Résolution N": "Resolution N",
    "Résolution (par arête)": "Resolution (per edge)",
    "Taille du domaine (m)": "Domain size (m)",
    "T initiale (°C)": "Initial T (°C)",
    "Durée simulée (s)": "Simulated duration (s)", "Images": "Frames",
    "Vitesse de lecture": "Playback speed", "Durée suggérée": "Suggested duration",
    "Lancer la simulation": "Run simulation", "Simuler": "Simulate",
    "Annuler": "Cancel", "Réinitialiser": "Reset", "Prêt.": "Ready.",
    "Objets": "Objects", "Obstacles": "Obstacles",
    "Sources de courant": "Current sources", "Parois du domaine": "Domain boundaries",
    "Ajouter": "Add", "Mettre à jour": "Update", "Dupliquer": "Duplicate",
    "Supprimer": "Delete", "Vider": "Clear", "Forme": "Shape",
    "Matériau": "Material", "Condition": "Condition",
    "Avancé — solveur numérique": "Advanced — numerical solver",
    "Cadre scientifique et limites": "Scientific scope and limitations",
    "Dynamique (transitoire / variable)": "Dynamics (transient / time-varying)",
    "Carte scalaire": "Scalar map", "Iso-valeurs": "Contours",
    "Champ (flèches)": "Field (arrows)", "Lignes de champ": "Field lines",
    "Intensité du champ": "Field magnitude", "Vue 2D": "2D view",
    "Vue 3D": "3D view", "Carte": "Map", "Flèches": "Arrows",
    "Sonde": "Probe", "Profil 1D": "1D profile",
    "Exporter l'image": "Export image", "Exporter l'animation": "Export animation",
    "Exporter CSV": "Export CSV", "Exporter PNG": "Export PNG",
    "Exporter la figure": "Export figure", "Exporter le champ": "Export field",
    "Exporter le rapport pédagogique": "Export teaching report",
    "Exporter le profil": "Export profile",
    "Rapport HTML (*.html)": "HTML report (*.html)",
    "Video MP4 (*.mp4);;Animation GIF (*.gif)":
        "MP4 video (*.mp4);;GIF animation (*.gif)",
    "Distance le long du segment (m)": "Distance along segment (m)",
    "Profil le long de la ligne": "Profile along a line", "Lecture": "Play",
    "Pause": "Pause", "Vitesse": "Speed", "Mode Expert": "Expert mode",
    "Mode : Expert": "Mode: Expert", "Mode : Cours": "Mode: Classroom",
    "Thème sombre": "Dark theme", "Panneau Contrôles": "Controls panel",
    "Présentation plein écran": "Full-screen presentation",
    "Indicateurs physiques...": "Physical indicators...",
    "Mémoriser le résultat comme référence A": "Store result as reference A",
    "Comparer le résultat courant B à A...": "Compare current result B with A...",
    "Afficher les hypothèses du modèle": "Show model assumptions",
    "À propos": "About", "Quitter": "Quit", "Ouvrir un projet FieldLab...": "Open FieldLab project...",
    "Sauvegarder le projet FieldLab...": "Save FieldLab project...",
    "Exporter la figure (PNG)...": "Export figure (PNG)...",
    "Exporter le champ scalaire (CSV)...": "Export scalar field (CSV)...",
    "Exporter l'animation (vidéo/GIF)...": "Export animation (video/GIF)...",
    "Exporter un rapport pédagogique (HTML)...": "Export teaching report (HTML)...",
    "Condensateur plan": "Parallel-plate capacitor",
    "Dipole (deux disques)": "Dipole (two disks)",
    "Cage de Faraday": "Faraday cage",
    "Pointe - plan (effet de pointe)": "Point-to-plane (field enhancement)",
    "Condensateur avec diélectrique partiel": "Capacitor with partial dielectric",
    "Fil unique": "Infinite wire", "Deux fils (opposes)": "Two wires (opposite currents)",
    "Deux fils (meme sens)": "Two wires (same direction)",
    "Boucle de courant (dipole)": "Current loop (dipole)",
    "Solenoide (coupe)": "Solenoid (cross-section)",
    "Bobines de Helmholtz (champ uniforme)": "Helmholtz coils (uniform field)",
    "Mur composite (verre + plastique)": "Composite wall (glass + plastic)",
    "Ailette de refroidissement": "Cooling fin",
    "Trempe (objet chaud dans l'eau)": "Quenching (hot object in water)",
    "Pont thermique": "Thermal bridge", "Plancher chauffant": "Underfloor heating",
    "Tuyau chaud (enceinte froide)": "Hot pipe (cold enclosure)",
    "Air (laboratoire)": "Air (laboratory)", "Eau": "Water", "Huile": "Oil",
    "Vide spatial": "Space vacuum", "Air": "Air", "Vide": "Vacuum",
    "Cuivre": "Copper", "Aluminium": "Aluminum", "Acier": "Steel",
    "Fer": "Iron", "Verre": "Glass", "Plastique": "Plastic",
    "Céramique": "Ceramic", "Ceramique": "Ceramic",
    "(aucun, vide normalise)": "(none, normalized vacuum)",
    "Scène libre (environnement personnalisé)": "Free scene (custom environment)",
    "Scène libre (objets et parois personnalisés)": "Free scene (custom objects and boundaries)",
    "Scalaire principal": "Primary scalar", "Coefficient matériau κ": "Material coefficient κ",
    "Plan de coupe": "Slice plane", "Haut": "Top", "Bas": "Bottom",
    "Gauche": "Left", "Droite": "Right", "Avant": "Front", "Arrière": "Back",
    "Potentiel imposé": "Fixed potential", "Température imposée": "Fixed temperature",
    "Source de chaleur": "Heat source", "Charge volumique": "Volume charge",
    "Matériau diélectrique": "Dielectric material",
    "Décoratif (sans effet physique)": "Decorative (no physical effect)",
    "Repère visuel (sans effet magnétique)": "Visual marker (no magnetic effect)",
    "Options de l'image": "Image options", "Options de l'animation": "Animation options",
    "Résolution": "Resolution", "Fond": "Background", "Blanc": "White",
    "Transparent": "Transparent", "Titre": "Title", "Facultatif": "Optional",
    "Durée de la vidéo": "Video duration", "Horodatage": "Timestamp",
    "Afficher le vrai temps simulé": "Show actual simulated time",
    "Français": "French", "Anglais": "English",
    "Export indisponible": "Export unavailable",
    "Aucun export disponible pour cet onglet.":
        "No export is available for this tab.",
    "Sauvegarder le projet": "Save project", "Ouvrir un projet": "Open project",
    "Projet FieldLab (*.fieldlab.json);;JSON (*.json)":
        "FieldLab project (*.fieldlab.json);;JSON (*.json)",
    "Projet FieldLab (*.fieldlab.json *.json);;JSON (*.json)":
        "FieldLab project (*.fieldlab.json *.json);;JSON (*.json)",
    "Sauvegarde impossible": "Cannot save", "Ouverture impossible": "Cannot open",
    "Importer un solide 3D": "Import a 3D solid", "STL discret": "Discrete STL",
    "Objet 3D invalide": "Invalid 3D object",
    "Modification impossible": "Cannot modify",
    "Transformation impossible": "Cannot transform",
    "Sauvegarder la scène": "Save scene", "Charger une scène": "Load scene",
    "Chargement impossible": "Cannot load", "Scène FieldLab (*.json)": "FieldLab scene (*.json)",
    "Solides 3D (*.stl *.step *.stp);;STL (*.stl);;STEP (*.step *.stp)":
        "3D solids (*.stl *.step *.stp);;STL (*.stl);;STEP (*.step *.stp)",
    "Un STL peut former seul le domaine tétraédrique. Pour des booléens OpenCASCADE, importez un STEP.":
        "An STL can form the tetrahedral domain by itself. Import STEP for OpenCASCADE boolean operations.",
    "Référence physique manquante": "Missing physical reference",
    "Scène 3D vide": "Empty 3D scene", "Champ trivial attendu": "Trivial field expected",
    "Ajoutez au moins un élément physique avant de lancer.":
        "Add at least one physical element before running.",
    "Lancer quand même ?": "Run anyway?",
    "Paramètres invalides": "Invalid parameters",
    "Paramètres incompatibles": "Incompatible parameters",
    "Calcul potentiellement lourd": "Potentially expensive computation",
    "Erreur de simulation": "Simulation error", "Rien a exporter": "Nothing to export",
    "Rien à exporter": "Nothing to export", "Erreur d'export": "Export error",
    "Analyse indisponible": "Analysis unavailable",
    "Indicateurs physiques": "Physical indicators",
    "Référence indisponible": "Reference unavailable",
    "Comparaison indisponible": "Comparison unavailable",
    "Comparaison impossible": "Cannot compare", "Comparaison A/B": "A/B comparison",
    "Un milieu physique réel est obligatoire en thermique transitoire. Sélectionnez Eau, Huile, Air ou un autre environnement : ρ·cp = 1 est une normalisation et ne représente pas une échelle de temps en secondes.":
        "A real physical medium is required for transient heat transfer. Select Water, Oil, Air, or another environment: ρ·cp = 1 is a normalization and does not represent a time scale in seconds.",
    "L'émissivité d'une paroi radiative doit être comprise entre 0 et 1.":
        "The emissivity of a radiating boundary must be between 0 and 1.",
    "La température radiative ambiante ne peut pas être sous le zéro absolu.":
        "The ambient radiation temperature cannot be below absolute zero.",
    "Le coefficient de convection h doit être positif ou nul.":
        "The convection coefficient h must be non-negative.",
    "Ce fichier n'est pas un projet FieldLab.": "This file is not a FieldLab project.",
    "Ce projet a été créé par une version plus récente de FieldLab.":
        "This project was created by a newer version of FieldLab.",
    "FieldLab — Simulateur multiphysique 2D/3D\n\nChamps électriques, magnétiques et thermiques :\néquations de Laplace/Poisson en 2D (différences finies et FEM)\net en 3D (FEM tétraédrique), régimes statique, variable\net transitoire, obstacles et matériaux réels.\n\nUn onglet par domaine, panneau de contrôle dockable,\nbascule 2D/3D dans chaque panneau.":
        "FieldLab — 2D/3D multiphysics simulator\n\nElectric, magnetic, and thermal fields:\n2D Laplace/Poisson equations (finite differences and FEM)\nand 3D tetrahedral FEM, steady, time-varying, and transient\nregimes, obstacles, and real materials.\n\nOne tab per domain, a dockable control panel,\nand a 2D/3D switch in each panel.",
}

# Complément exhaustif des panneaux métier. Les termes courts qui sont aussi
# des identifiants (``dirichlet``, ``boite``...) restent stockés en français
# dans ComboBoxTraduit ; seule leur représentation visible passe en anglais.
EN.update({
    "3D : scénarios sur un vrai maillage tétraédrique (éléments finis). « Scène libre » permet de créer l'environnement ; les scénarios prédéfinis sont verrouillés.":
        "3D: scenarios use a real tetrahedral finite-element mesh. Free scene lets you create the environment; presets are locked.",
    "A_z = 0 (Dirichlet) confine le flux dans la boite.\nPasser en Neumann pour laisser le champ sortir.":
        "A_z = 0 (Dirichlet) confines the flux inside the box.\nUse Neumann to let the field leave the domain.",
    "Absorption α (0-1)": "Absorptivity α (0-1)",
    "Accrochage": "Snapping", "Angle incidence (°)": "Incidence angle (°)",
    "Appliquer à cette paroi": "Apply to this boundary", "Axes": "Axes",
    "Atmosphere terrestre (exterieur)": "Earth atmosphere (outdoors)",
    "Câble coaxial": "Coaxial cable", "Cable coaxial": "Coaxial cable",
    "Charger JSON": "Load JSON", "Circuit": "Circuit",
    "Circuit Biot–Savart (air/vide)": "Biot–Savart circuit (air/vacuum)",
    "Coin chaud": "Hot corner", "Composant chaud": "Hot component",
    "Condensateur + obstacle conducteur": "Capacitor + conducting obstacle",
    "Condensateur + obstacle isolant": "Capacitor + insulating obstacle",
    "Condensateur en coin": "Corner capacitor",
    "Condensateur plan (deux plaques)": "Parallel-plate capacitor (two plates)",
    "Conditions appliquées aux six faces externes de la boîte : adiabatique, température imposée, convection, rayonnement ou flux thermique imposé.":
        "Conditions on the six outer faces: adiabatic, fixed temperature, convection, radiation, or prescribed heat flux.",
    "Conditions appliquées aux six faces externes de la boîte. Une isolation impose un flux électrique normal nul ; un potentiel imposé fixe V sur toute la face.":
        "Conditions on the six outer faces. Insulation sets the normal electric flux to zero; fixed potential sets V on the whole face.",
    "Conditions aux limites du domaine 3D": "3D domain boundary conditions",
    "Construisez la scène avant le calcul. Sélectionnez un objet dans la liste ou directement dans l’aperçu 3D.":
        "Build the scene before computing. Select an object in the list or directly in the 3D preview.",
    "Convection": "Convection", "Coquille spherique (maillage gmsh)":
        "Spherical shell (gmsh mesh)", "Cote": "Side", "Côté": "Side",
    "Courant (A)": "Current (A)", "Creneau": "Square wave",
    "Cube + sphere cuivre (obstacle/materiau)":
        "Cube + copper sphere (obstacle/material)",
    "Cube + sphere plastique (obstacle/materiau)":
        "Cube + plastic sphere (obstacle/material)",
    "Cube - deux electrodes (V)": "Cube — two electrodes (V)",
    "Cube - regime variable (electrode sinusoidale)":
        "Cube — time-varying sinusoidal electrode",
    "Cube convection (Robin, 6 faces)": "Convection cube (Robin, 6 faces)",
    "Câble coaxial (âme + blindage)": "Coaxial cable (core + shield)",
    "Densité de courant J (A/m²)": "Current density J (A/m²)",
    "Deux blocs chauds": "Two hot blocks", "Deux fils (opposés)":
        "Two wires (opposite currents)", "Déplacer / tourner": "Move / rotate",
    "Echangeur (obstacle isolant)": "Heat exchanger (insulating obstacle)",
    "Echelon": "Step", "Electrodes circulaires": "Circular electrodes",
    "Fil (disque-source) ou barre (rectangle-source) avec J en A/m².\n+ = courant sortant (rouge) ;  - = courant entrant (bleu)":
        "Wire (disk source) or bar (rectangular source), with J in A/m².\n+ = outgoing current (red); − = incoming current (blue)",
    "Fil rectiligne (anneaux de B)": "Straight wire (B rings)",
    "Flux absorbé : 900.0 W/m²  (réflexion ρ = 0.10)":
        "Absorbed flux: 900.0 W/m² (reflection ρ = 0.10)",
    "Calcule le flux absorbé q = α · flux solaire · cos(angle d'incidence) et l'applique à la paroi choisie (type « flux »).":
        "Computes the absorbed flux q = α · solar flux · cos(incidence angle) and applies it to the selected boundary (flux type).",
    "Flux solaire (W/m²)": "Solar flux (W/m²)",
    "Flux thermique imposé": "Prescribed heat flux", "Fréquence (Hz)": "Frequency (Hz)",
    "Importer STL / STEP": "Import STL / STEP", "Impulsions": "Pulses",
    "Isolant électrique": "Electrical insulator",
    "Isolation électrique (flux normal nul)": "Electrical insulation (zero normal flux)",
    "Itér. max": "Max iterations", "La scène ne contient ni valeur imposée ni source : le champ sera constant/nul.":
        "The scene contains neither a fixed value nor a source: the field will be constant/zero.",
    "Le modèle 2D est une coupe d'une géométrie invariante selon z. Une charge saisie est donc une densité volumique ρ (C/m³), constante hors du plan.":
        "The 2D model is a cross-section of a geometry invariant along z. An entered charge is therefore a volume density ρ (C/m³), constant out of plane.",
    "Lentille electrostatique": "Electrostatic lens",
    "Ligne bifilaire": "Two-wire line",
    "Ligne bifilaire (deux cylindres ±V)": "Two-wire line (two cylinders ±V)",
    "Matériau qui remplit le volume hors objets. Il fixe κ et ρ·cp, donc l'échelle de temps physique du transitoire.":
        "Material filling the volume outside objects. It sets κ and ρ·cp, hence the physical transient time scale.",
    "Micro-ruban (microstrip)": "Microstrip", "Milieu": "Medium",
    "Milieu ambiant qui remplit le domaine (hors obstacles/matériaux placés explicitement) : modifie la conductivité/permittivité/perméabilité de fond.":
        "Ambient medium filling the domain outside explicit objects/materials; it changes the background conductivity, permittivity, or permeability.",
    "Mur (gradient 1D)": "Wall (1D gradient)",
    "Mur (gradient 1D) - cube chauffe": "Wall (1D gradient) — heated cube",
    "Méthode": "Method", "Nappe de courant": "Current sheet",
    "Nom": "Name", "Noyaux (matériau magnétique)": "Cores (magnetic material)",
    "Objet rempli d'un materiau reel (fer/acier : concentrent le\nflux ; autres materiaux : sans effet magnetique).":
        "Object filled with a real material (iron/steel concentrate flux; other materials have no magnetic effect).",
    "Oméga (SOR)": "Omega (SOR)", "Oméga optimal": "Optimal omega",
    "Opération CAO": "CAD operation",
    "Par défaut : FEM (direct) — précis, rapide, et seul à prendre en compte matériaux et parois convection/rayonnement/flux. Les solveurs itératifs (Jacobi, Gauss-Seidel, SOR) sont proposés à titre pédagogique.":
        "Default: direct FEM — accurate, fast, and the only method handling materials and convection/radiation/flux boundaries. Iterative solvers are provided for teaching.",
    "Paramètres temporels du scénario sélectionné. Le pas de temps interne vaut durée/(images×5), schéma implicite stable.":
        "Time parameters for the selected scenario. The internal step is duration/(frames×5), using a stable implicit scheme.",
    "Paroi adiabatique": "Adiabatic boundary", "Peigne interdigite": "Interdigitated comb",
    "Placer au clic sur la carte": "Place by clicking the map",
    "Placement actif — cliquez sur la carte": "Placement active — click the map",
    "Polyligne x,y,z; …": "Polyline x,y,z; …", "Potentiel imposé V (V)": "Fixed potential V (V)",
    "Primitive": "Primitive", "Primitive et rôle physique": "Primitive and physical role",
    "Processeur (4 blocs chauds)": "Processor (4 hot blocks)",
    "Quadripole": "Quadrupole", "Quadripole magnetique": "Magnetic quadrupole",
    "Quatre parois": "Four boundaries", "Raffinement (FEM)": "Refinement (FEM)",
    "Rayonnement": "Radiation", "Rayonnement solaire (assistant)": "Solar radiation assistant",
    "Redimensionner": "Resize", "Rétablir": "Restore", "Rôle": "Role",
    "Sauvegarder JSON": "Save JSON",
    "Scène libre : ajoutez vos objets, sources et conditions aux limites, puis placez-les au clic dans l’aperçu.":
        "Free scene: add objects, sources, and boundary conditions, then place them by clicking the preview.",
    "Scénario prédéfini : sa géométrie est définie par le modèle. Choisissez « Scène libre » pour ajouter, déplacer ou redimensionner des objets.":
        "Preset scenario: its geometry is defined by the model. Choose Free scene to add, move, or resize objects.",
    "Silicium": "Silicon", "Sinusoidale": "Sine wave",
    "Solénoïde (12 spires)": "Solenoid (12 turns)", "Sphere chauffee (maillage gmsh + source)":
        "Heated sphere (gmsh mesh + source)", "Spire (dipôle magnétique)": "Loop (magnetic dipole)",
    "Spires": "Turns", "Stationnaire : amplitude constante.": "Steady: constant amplitude.",
    "Variable : amplitude animée dans le temps (lecteur temporel), par résolutions stationnaires successives indépendantes (approximation quasi-statique).":
        "Time-varying: amplitude animated through independent steady solves (quasi-static approximation).",
    "Stationnaire : état d'équilibre final.": "Steady: final equilibrium state.",
    "Transitoire : évolution dans le temps depuis la température initiale (lecteur temporel). Les temps affichés sont physiques (inertie ρ·cp réelle des matériaux et du milieu ambiant ; milieu « aucun » = temps normalisé).":
        "Transient: time evolution from the initial temperature. Displayed times are physical and use the real ρ·cp of materials and ambient medium; no medium means normalized time.",
    "Sélectionnez un milieu pour calculer τ = L²/α.": "Select a medium to compute τ = L²/α.",
    "Taille maille CAO (m)": "CAD mesh size (m)", "Tension V (V)": "Voltage V (V)",
    "Tolérance": "Tolerance", "Type": "Type", "Éditeur visuel de scène 3D": "Visual 3D scene editor",
    "Élément": "Element", "Différence": "Difference",
    "Intersection": "Intersection", "Union": "Union",
    "aucune": "none", "anneau": "ring", "barre (rectangle)": "bar (rectangle)",
    "bas": "bottom", "boite": "box", "conducteur": "conductor",
    "cylindre": "cylinder", "decoratif": "decorative", "disque": "disk",
    "domaine": "domain", "droite": "right", "electrode": "electrode",
    "fil": "wire", "fil (disque)": "wire (disk)", "gauche": "left",
    "haut": "top", "isolant": "insulator", "longueur": "length",
    "maillage_importe": "imported_mesh", "materiau": "material",
    "polyligne": "polyline", "rayon": "radius", "rectangle": "rectangle",
    "segment_h": "horizontal_segment", "segment_v": "vertical_segment",
    "solenoide": "solenoid", "source": "source", "sphere": "sphere",
    "spire": "loop", "taille": "size",
    "neumann : bord libre  ·  dirichlet : tension imposée (V)":
        "neumann: free boundary · dirichlet: fixed voltage (V)",
    "neumann : isolée  ·  dirichlet : T imposée  ·  robin : convection (h, T∞)  ·  radiation : rayonnement (ε, T∞)  ·  flux : flux imposé (q, W/m², chauffage solaire par ex.) — robin/radiation/flux : solveur FEM":
        "neumann: insulated · dirichlet: fixed T · robin: convection (h, T∞) · radiation (ε, T∞) · flux: prescribed q (W/m², e.g. solar heating) — robin/radiation/flux require FEM",
})

EN.update({
    "Modèle": "Model", "régime": "regime", "scénario": "scenario",
    "Choisissez une situation classique de cours prête à simuler.":
        "Choose a ready-to-run classroom scenario.",
    "Calcule le champ avec les paramètres affichés.":
        "Computes the field using the displayed parameters.",
    "Densité de courant hors du plan, en ampères par mètre carré.":
        "Out-of-plane current density, in amperes per square metre.",
    "Différence de potentiel imposée aux électrodes, en volts.":
        "Potential difference applied to the electrodes, in volts.",
    "Longueur physique du côté du domaine, en mètres.":
        "Physical side length of the domain, in metres.",
    "Stationnaire montre l'équilibre; transitoire montre l'évolution réelle.":
        "Steady shows equilibrium; transient shows the physical evolution.",
    "Température maintenue sur l'objet chaud, en degrés Celsius.":
        "Temperature maintained on the hot object, in degrees Celsius.",
    "Calques :": "Layers:", "Face": "Front", "Dessus": "Top",
    "Recentrer": "Reset camera", "Opacité": "Opacity", "Arêtes": "Edges",
    "Grille": "Grid", "Fond sombre": "Dark background",
    "Iso-surfaces": "Isosurfaces", "Maillage": "Mesh", "Coupe": "Slice",
    "Coupe — Normale": "Slice — Normal", "Position": "Position",
    "Plans": "Planes", "Iso-lignes": "Contour lines",
    "Vecteurs plan": "In-plane vectors", "Lignes plan": "In-plane lines",
    "Manipuler le plan": "Manipulate plane", "Clip boîte": "Box clip",
    "Plage iso min/max": "Isovalue range min/max",
    "Source lignes": "Line source", "Densité": "Density", "Tubes": "Tubes",
    "Flèches pas/taille": "Arrow spacing/size", "Graines": "Seeds",
    "Voir graines": "Show seeds", "Sonde-ligne": "Line probe",
    "Volume": "Volume", "Plan": "Plane", "Surface": "Surface", "Ligne": "Line",
    "Oblique": "Oblique", "Début": "Start", "Temps": "Time",
    "Crée un PNG 1080p, 1440p ou 4K avec unités et colorbar.":
        "Creates a 1080p, 1440p, or 4K PNG with units and colorbar.",
    "Crée un GIF ou MP4 horodaté à partir du résultat temporel.":
        "Creates a timestamped GIF or MP4 from a time-dependent result.",
    "Cliquez pour épingler jusqu'à cinq valeurs sur la carte.":
        "Click to pin up to five values on the map.",
    "Cliquez deux extrémités pour tracer la grandeur le long d'une ligne.":
        "Click two endpoints to plot the quantity along a line.",
    "Répartition des graines des lignes de champ : Volume (tout l'espace, défaut), Plan, Surface ou Ligne":
        "Field-line seed distribution: Volume (whole space, default), Plane, Surface, or Line",
    "Diagnostic : afficher les points d'ensemencement":
        "Diagnostic: show seed points",
    "Les propriétés de matériaux sont des ordres de grandeur pédagogiques, pas des données certifiées de conception.":
        "Material properties are teaching-scale estimates, not certified design data.",
    "Approximation électrostatique/quasi-statique : induction et propagation électromagnétique non modélisées.":
        "Electrostatic/quasi-static approximation: induction and electromagnetic propagation are not modeled.",
    "Les métaux placés comme matériaux sont approchés par une très forte permittivité ; une électrode imposée représente mieux un conducteur idéal.":
        "Metals used as materials are approximated by a very high permittivity; a fixed-potential electrode better represents an ideal conductor.",
    "Une paroi de Neumann impose un flux normal nul : ce n'est pas une frontière ouverte à l'infini.":
        "A Neumann boundary sets normal flux to zero; it is not an open boundary at infinity.",
    "Biot–Savart dans l'air/le vide pour des fils minces : valeurs en teslas, sans noyau magnétique ni courant induit.":
        "Biot–Savart in air/vacuum for thin wires: values in teslas, without magnetic cores or induced currents.",
    "Coupe 2D supposée infinie dans la direction hors plan ; J_z est en A/m², A_z en T·m et B en teslas ; le facteur μ₀ est inclus dans l'équation.":
        "The 2D cross-section is assumed infinite out of plane; J_z is in A/m², A_z in T·m and B in teslas; μ₀ is included in the equation.",
    "Matériaux magnétiques linéaires : saturation, hystérésis et courants de Foucault non modélisés.":
        "Linear magnetic materials: saturation, hysteresis, and eddy currents are not modeled.",
    "Conduction thermique uniquement dans le domaine ; convection et rayonnement n'agissent que sur les parois configurées.":
        "Heat conduction only inside the domain; convection and radiation act only on configured boundaries.",
    "Le rayonnement est linéarisé autour de la température ambiante : prudence pour les écarts de température très élevés.":
        "Radiation is linearized around ambient temperature; use caution for very large temperature differences.",
    "Le transitoire utilise ρ·cp et un schéma implicite ; le pas de temps influence la précision, même si le schéma reste stable.":
        "The transient model uses ρ·cp and an implicit scheme; the time step affects accuracy even though the scheme remains stable.",
    "Champ des circuits dans le vide — les matériaux magnétiques ne sont pas pris en compte en 3D (Biot–Savart). Les primitives 3D sont uniquement décoratives.":
        "Circuit field in vacuum — magnetic materials are not included in 3D (Biot–Savart). 3D primitives are decorative only.",
    "Aucun circuit dans la scène : le champ B sera nul. Ajoutez un fil, une spire ou une bobine (élément “Circuit”).":
        "No circuit in the scene: B will be zero. Add a wire, loop, or coil (Circuit element).",
    "Potentiel A_z (T·m)  ·  Champ B (T)":
        "Vector potential A_z (T·m) · Magnetic field B (T)",
    "Potentiel V (V)  ·  Champ E (V/m)":
        "Potential V (V) · Electric field E (V/m)",
    "Température T (°C)  ·  Flux thermique (W/m²)":
        "Temperature T (°C) · Heat flux (W/m²)",
    "Potentiel imposé : tension V fixée  ·  Isolant électrique : bloque le champ\nMatériau diélectrique : permittivité réelle (solveur FEM)\nCharge volumique : ρ en C/m³, avec −div(εᵣ∇V)=ρ/ε₀":
        "Fixed potential: prescribed voltage V · Electrical insulator: blocks the field\nDielectric material: real permittivity (FEM solver)\nVolume charge: ρ in C/m³, with −div(εᵣ∇V)=ρ/ε₀",
    "Température imposée : bloc à T (°C) constante\nMatériau thermique : conductivité k réelle (solveur FEM)":
        "Fixed temperature: block held at constant T (°C)\nThermal material: real conductivity k (FEM solver)",
    "Température imposée T (°C)": "Fixed temperature T (°C)",
    "Stationnaire : amplitude constante.\nVariable : amplitude animée dans le temps (lecteur temporel), par résolutions stationnaires successives indépendantes (approximation quasi-statique).":
        "Steady: constant amplitude.\nTime-varying: animated amplitude from independent successive steady solves (quasi-static approximation).",
    "Stationnaire : état d'équilibre final.\nTransitoire : évolution dans le temps depuis la température initiale (lecteur temporel). Les temps affichés sont physiques (inertie ρ·cp réelle des matériaux et du milieu ambiant ; milieu « aucun » = temps normalisé).":
        "Steady: final equilibrium.\nTransient: evolution from the initial temperature. Displayed times are physical and use the real ρ·cp of materials and ambient medium; no medium means normalized time.",
    "X− · gauche": "X− · left", "X+ · droite": "X+ · right",
    "Y− · avant": "Y− · front", "Y+ · arrière": "Y+ · rear",
    "Z− · bas": "Z− · bottom", "Z+ · haut": "Z+ · top",
})


_REMPLACEMENTS = (
    ("Prêt", "Ready"), ("Calcule le", "Computes the"),
    ("Calcul en cours", "Computing"),
    ("Calcul", "Computing"), ("Terminé", "Completed"),
    ("Erreur", "Error"), ("Aucune", "No"), ("Aucun", "No"),
    ("Lancez d'abord une simulation", "Run a simulation first"),
    ("Figure exportée", "Figure exported"),
    ("Animation exportée", "Animation exported"),
    ("Champ exporté", "Field exported"),
    ("Projet sauvegardé", "Project saved"),
    ("Projet chargé", "Project loaded"),
    ("relancez les simulations", "rerun the simulations"),
    ("relancez la simulation", "rerun the simulation"),
    ("Flux absorbé", "Absorbed flux"), ("réflexion", "reflection"),
    ("Conduction pure", "Pure conduction"),
    ("la convection naturelle n'est pas modélisée", "natural convection is not modeled"),
    ("dans un fluide réel, le réchauffement serait plus rapide", "heating would be faster in a real fluid"),
    ("Durée", "Duration"), ("Température", "Temperature"),
    ("Matériau diélectrique", "Dielectric material"),
    ("Matériau thermique", "Thermal material"),
    ("Matériau", "Material"), ("matériau", "material"),
    ("Isolation électrique (flux normal nul)",
     "Electrical insulation (zero normal flux)"),
    ("Paroi adiabatique", "Adiabatic boundary"),
    ("Résumé", "Summary"), ("parois", "boundaries"),
    ("paroi", "boundary"), ("matériaux", "materials"),
    ("milieu", "medium"), ("scénario", "scenario"),
    ("Acier", "Steel"), ("Cuivre", "Copper"),
    ("Aluminium", "Aluminum"), ("Eau", "Water"),
    ("Huile", "Oil"), ("Fer", "Iron"), ("Verre", "Glass"),
    ("Plastique", "Plastic"), ("Ceramique", "Ceramic"),
    ("Vide", "Vacuum"),
)


def definir_langue(langue: str):
    global _langue
    if langue not in {"fr", "en"}:
        raise ValueError(f"Langue inconnue : {langue!r}")
    _langue = langue


def langue_courante() -> str:
    return _langue


def tr(texte):
    if _langue != "en" or not isinstance(texte, str) or not texte:
        return texte
    if texte in EN:
        return EN[texte]
    resultat = texte
    for francais, anglais in _REMPLACEMENTS:
        motif = re.escape(francais)
        if francais[0].isalnum():
            motif = r"(?<!\w)" + motif
        if francais[-1].isalnum():
            motif += r"(?!\w)"
        resultat = re.sub(motif, anglais, resultat)
    return resultat


def _traduire_propriete(objet, nom_propriete, lire, ecrire):
    cle = f"_i18n_source_{nom_propriete}"
    source = objet.property(cle)
    if source is None:
        source = lire()
        objet.setProperty(cle, source)
    ecrire(tr(source))


def traduire_interface(racine: QObject):
    """Retraduit en place les textes visibles de toute une fenêtre Qt."""

    objets = [racine] + racine.findChildren(QObject)
    for objet in objets:
        if hasattr(objet, "appliquer_langue"):
            objet.appliquer_langue()
        if isinstance(objet, QLabel):
            _traduire_propriete(objet, "text", objet.text, objet.setText)
        elif isinstance(objet, QAbstractButton):
            _traduire_propriete(objet, "text", objet.text, objet.setText)
        if isinstance(objet, QGroupBox):
            _traduire_propriete(objet, "title", objet.title, objet.setTitle)
        if isinstance(objet, QAction):
            _traduire_propriete(objet, "text", objet.text, objet.setText)
        if isinstance(objet, QMenu):
            _traduire_propriete(objet, "title", objet.title, objet.setTitle)
        if isinstance(objet, QTabWidget):
            sources = objet.property("_i18n_sources_onglets")
            if sources is None or len(sources) != objet.count():
                sources = [objet.tabText(i) for i in range(objet.count())]
                objet.setProperty("_i18n_sources_onglets", sources)
            for index, source in enumerate(sources):
                objet.setTabText(index, tr(source))
        if isinstance(objet, QDockWidget):
            _traduire_propriete(
                objet, "windowTitle", objet.windowTitle, objet.setWindowTitle)
        if isinstance(objet, QMainWindow):
            _traduire_propriete(
                objet, "windowTitle", objet.windowTitle, objet.setWindowTitle)
        elif isinstance(objet, QDialog) and objet.windowTitle():
            _traduire_propriete(
                objet, "windowTitle", objet.windowTitle, objet.setWindowTitle)
        if isinstance(objet, QLineEdit) and objet.placeholderText():
            _traduire_propriete(
                objet, "placeholder", objet.placeholderText,
                objet.setPlaceholderText)
        if hasattr(objet, "toolTip") and objet.toolTip():
            _traduire_propriete(
                objet, "tooltip", objet.toolTip, objet.setToolTip)
