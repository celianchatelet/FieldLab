import copy
from pathlib import Path
import numpy as np
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
)

from fieldlab.fem3d.scene import ItemGeometrie, OPERATIONS_CAO, Scene3D
from fieldlab.fem3d.scene_editor import (
    TYPES_CIRCUITS, angles_euler_depuis_matrice, centre_item,
    circuits_depuis_parametres, contraindre_affine_dans_domaine,
    matrice_rotation_euler, params_primitive, transformer_element_affine,
)
from fieldlab.materials import NOMS_MATERIAUX


def _spin(valeur=0.0, minimum=-1.0e6, maximum=1.0e6, pas=0.05):
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(4)
    spin.setSingleStep(pas)
    spin.setValue(valeur)
    return spin


class SceneEditorPanel(QGroupBox):
    def __init__(self, domaine_nom, callback_scene=None, parent=None):
        super().__init__("Éditeur visuel de scène 3D", parent)
        self.domaine_nom = domaine_nom
        self.callback_scene = callback_scene
        self.scene = Scene3D(
            1.0, ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)))
        self._chargement_formulaire = False
        self._restauration_historique = False
        self._historique = []
        self._index_historique = -1
        self._build()
        self._rafraichir_liste()
        self._enregistrer_historique(force=True)
        self._maj_diagnostic()

    def _build(self):
        layout = QVBoxLayout(self)
        info = QLabel(
            "Construisez la scène avant le calcul. Sélectionnez un objet "
            "dans la liste ou directement dans l’aperçu 3D.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)

        outils = QGridLayout()
        self.btn_deplacer = QPushButton("Déplacer / tourner")
        self.btn_deplacer.setCheckable(True)
        self.btn_deplacer.setChecked(True)
        self.btn_redimensionner = QPushButton("Redimensionner")
        self.btn_redimensionner.setCheckable(True)
        groupe_outils = QButtonGroup(self)
        groupe_outils.setExclusive(True)
        groupe_outils.addButton(self.btn_deplacer)
        groupe_outils.addButton(self.btn_redimensionner)
        self.btn_deplacer.toggled.connect(self._changer_outil)
        self.btn_redimensionner.toggled.connect(self._changer_outil)
        outils.addWidget(self.btn_deplacer, 0, 0)
        outils.addWidget(self.btn_redimensionner, 0, 1)
        self.cb_axes = QComboBox()
        self.cb_axes.addItems(["XYZ", "X", "Y", "Z", "XY", "XZ", "YZ"])
        outils.addWidget(QLabel("Axes"), 0, 2)
        outils.addWidget(self.cb_axes, 0, 3)
        self.chk_accrochage = QCheckBox("Accrochage")
        self.chk_accrochage.setChecked(True)
        outils.addWidget(self.chk_accrochage, 1, 0)
        self.spin_pas_grille = _spin(0.05, 0.0001, 1000.0, 0.01)
        self.spin_pas_grille.setSuffix(" m")
        outils.addWidget(self.spin_pas_grille, 1, 1)
        self.btn_annuler = QPushButton("Annuler")
        self.btn_annuler.clicked.connect(self.annuler)
        self.btn_retablir = QPushButton("Rétablir")
        self.btn_retablir.clicked.connect(self.retablir)
        outils.addWidget(self.btn_annuler, 1, 2)
        outils.addWidget(self.btn_retablir, 1, 3)
        layout.addLayout(outils)
        self.label_diagnostic = QLabel()
        self.label_diagnostic.setWordWrap(True)
        layout.addWidget(self.label_diagnostic)
        QShortcut(QKeySequence.StandardKey.Undo, self).activated.connect(
            self.annuler)
        QShortcut(QKeySequence.StandardKey.Redo, self).activated.connect(
            self.retablir)

        domaine = QGridLayout()
        self.spin_lx = _spin(1.0, 0.001, 1000.0, 0.1)
        self.spin_ly = _spin(1.0, 0.001, 1000.0, 0.1)
        self.spin_lz = _spin(1.0, 0.001, 1000.0, 0.1)
        self.cb_ambiant = QComboBox()
        self.cb_ambiant.addItems(
            ["Air", "Vide"] if self.domaine_nom == "Magnetostatique"
            else NOMS_MATERIAUX)
        self.cb_ambiant.setCurrentText("Air")
        self.spin_maille_cao = _spin(0.05, 0.00001, 1000.0, 0.01)
        for i, (texte, widget) in enumerate((
                ("Lx (m)", self.spin_lx), ("Ly (m)", self.spin_ly),
                ("Lz (m)", self.spin_lz), ("Milieu", self.cb_ambiant))):
            ligne, paire = divmod(i, 2)
            domaine.addWidget(QLabel(texte), ligne, 2 * paire)
            domaine.addWidget(widget, ligne, 2 * paire + 1)
        layout.addLayout(domaine)
        ligne_cao = QGridLayout()
        ligne_cao.addWidget(QLabel("Taille maille CAO (m)"), 0, 0)
        ligne_cao.addWidget(self.spin_maille_cao, 0, 1)
        self.cb_operation_cao = QComboBox()
        self.cb_operation_cao.addItems(list(OPERATIONS_CAO))
        ligne_cao.addWidget(QLabel("Opération CAO"), 1, 0)
        ligne_cao.addWidget(self.cb_operation_cao, 1, 1)
        self.bouton_import = QPushButton("Importer STL / STEP")
        self.bouton_import.clicked.connect(self.importer_cao)
        ligne_cao.addWidget(self.bouton_import, 0, 2, 2, 1)
        layout.addLayout(ligne_cao)
        for spin in (self.spin_lx, self.spin_ly, self.spin_lz):
            spin.valueChanged.connect(self._changer_domaine)
        self.cb_ambiant.currentTextChanged.connect(self._changer_domaine)
        self.spin_maille_cao.valueChanged.connect(self._changer_domaine)

        choix = QHBoxLayout()
        self.cb_nature = QComboBox()
        self.cb_nature.addItems(
            ["Primitive", "Circuit"]
            if self.domaine_nom == "Magnetostatique" else ["Primitive"])
        self.cb_nature.currentTextChanged.connect(self._maj_nature)
        self.edit_label = QLineEdit("Objet")
        choix.addWidget(QLabel("Élément"))
        choix.addWidget(self.cb_nature)
        choix.addWidget(QLabel("Nom"))
        choix.addWidget(self.edit_label, stretch=1)
        layout.addLayout(choix)

        self.groupe_primitive = QGroupBox("Primitive et rôle physique")
        gp = QGridLayout(self.groupe_primitive)
        self.cb_forme = QComboBox()
        self.cb_forme.addItems(["boite", "sphere", "cylindre", "maillage_importe"])
        self.cb_role = QComboBox()
        roles = (["decoratif", "conducteur"] if self.domaine_nom == "Magnetostatique"
                 else ["electrode", "isolant", "materiau", "source",
                       "conducteur", "decoratif"])
        self.cb_role.addItems(roles)
        self.cb_materiau = QComboBox(); self.cb_materiau.addItems(NOMS_MATERIAUX)
        self.spin_valeur = _spin(0.0)
        self.spin_q = _spin(0.0)
        for i, (texte, widget) in enumerate((
                ("Forme", self.cb_forme), ("Rôle", self.cb_role),
                ("Matériau", self.cb_materiau), ("Valeur", self.spin_valeur),
                ("q", self.spin_q))):
            ligne, paire = divmod(i, 2)
            gp.addWidget(QLabel(texte), ligne, 2 * paire)
            gp.addWidget(widget, ligne, 2 * paire + 1)
        layout.addWidget(self.groupe_primitive)

        geometrie = QGridLayout()
        self.spin_x = _spin(0.5); self.spin_y = _spin(0.5); self.spin_z = _spin(0.5)
        self.spin_r = _spin(0.1, 0.001, 1000.0, 0.01)
        self.spin_dx = _spin(0.2, 0.001, 1000.0, 0.01)
        self.spin_dy = _spin(0.2, 0.001, 1000.0, 0.01)
        self.spin_dz = _spin(0.2, 0.001, 1000.0, 0.01)
        self.spin_longueur = _spin(0.6, 0.001, 1000.0, 0.05)
        self.spin_rx = _spin(0.0, -360.0, 360.0, 5.0)
        self.spin_ry = _spin(0.0, -360.0, 360.0, 5.0)
        self.spin_rz = _spin(0.0, -360.0, 360.0, 5.0)
        champs = (
            ("x", self.spin_x), ("y", self.spin_y), ("z", self.spin_z),
            ("rayon", self.spin_r), ("Lx", self.spin_dx),
            ("Ly", self.spin_dy), ("Lz", self.spin_dz),
            ("longueur", self.spin_longueur), ("rot X°", self.spin_rx),
            ("rot Y°", self.spin_ry), ("rot Z°", self.spin_rz),
        )
        for i, (texte, widget) in enumerate(champs):
            ligne, paire = divmod(i, 2)
            geometrie.addWidget(QLabel(texte), ligne, 2 * paire)
            geometrie.addWidget(widget, ligne, 2 * paire + 1)
        layout.addLayout(geometrie)

        self.groupe_circuit = QGroupBox("Circuit Biot–Savart (air/vide)")
        gc = QGridLayout(self.groupe_circuit)
        self.cb_circuit = QComboBox(); self.cb_circuit.addItems(list(TYPES_CIRCUITS))
        self.spin_courant = _spin(5.0)
        self.spin_spires = QSpinBox()
        self.spin_spires.setRange(1, 500)
        self.spin_spires.setValue(12)
        self.edit_polyligne = QLineEdit("0.2,0.5,0.5; 0.8,0.5,0.5")
        gc.addWidget(QLabel("Type"), 0, 0); gc.addWidget(self.cb_circuit, 0, 1)
        gc.addWidget(QLabel("Courant (A)"), 0, 2); gc.addWidget(self.spin_courant, 0, 3)
        gc.addWidget(QLabel("Spires"), 0, 4); gc.addWidget(self.spin_spires, 0, 5)
        gc.addWidget(QLabel("Polyligne x,y,z; …"), 1, 0)
        gc.addWidget(self.edit_polyligne, 1, 1, 1, 7)
        layout.addWidget(self.groupe_circuit)

        actions = QGridLayout()
        for i, (texte, slot) in enumerate((
                ("Ajouter", self.ajouter), ("Mettre à jour", self.mettre_a_jour),
                ("Dupliquer", self.dupliquer), ("Supprimer", self.supprimer),
                ("Sauvegarder JSON", self.sauvegarder),
                ("Charger JSON", self.charger))):
            bouton = QPushButton(texte); bouton.clicked.connect(slot)
            ligne, colonne = divmod(i, 3)
            actions.addWidget(bouton, ligne, colonne)
        layout.addLayout(actions)
        self.liste = QListWidget()
        self.liste.setMaximumHeight(125)
        self.liste.currentRowChanged.connect(self._charger_selection)
        layout.addWidget(self.liste)
        self._maj_nature()

    @property
    def index_selectionne(self):
        return self.liste.currentRow()

    @property
    def mode_transformation(self):
        return ("Redimensionner" if self.btn_redimensionner.isChecked()
                else "Déplacer / tourner")

    def _changer_outil(self, actif):
        if actif:
            self._notifier(modifie=False)

    def _enregistrer_historique(self, force=False):
        if self._restauration_historique:
            return
        etat = self.scene.to_dict()
        if (not force and self._historique
                and etat == self._historique[self._index_historique]):
            return
        del self._historique[self._index_historique + 1:]
        self._historique.append(copy.deepcopy(etat))

        if len(self._historique) > 100:
            del self._historique[0]
        self._index_historique = len(self._historique) - 1
        self._maj_boutons_historique()

    def _maj_boutons_historique(self):
        self.btn_annuler.setEnabled(self._index_historique > 0)
        self.btn_retablir.setEnabled(
            0 <= self._index_historique < len(self._historique) - 1)

    def _restaurer_historique(self, index):
        if not 0 <= index < len(self._historique):
            return
        self._restauration_historique = True
        try:
            self._index_historique = index
            self.scene = Scene3D.from_dict(
                copy.deepcopy(self._historique[index]))
            self._charger_domaine()
            selection = min(
                max(self.index_selectionne, 0),
                len(self.scene.items) + len(self.scene.circuits) - 1)
            self._rafraichir_liste(selection)
            if selection >= 0:
                self._charger_selection(selection)
        finally:
            self._restauration_historique = False
        self._maj_boutons_historique()
        self._maj_diagnostic()
        if self.callback_scene is not None:
            self.callback_scene(
                self.scene, self.index_selectionne, True)

    def annuler(self):
        self._restaurer_historique(self._index_historique - 1)

    def retablir(self):
        self._restaurer_historique(self._index_historique + 1)

    def _changer_domaine(self, *_args):
        if self._chargement_formulaire:
            return
        dimensions = (self.spin_lx.value(), self.spin_ly.value(), self.spin_lz.value())
        self.scene.taille_m = max(dimensions)
        self.scene.boite_domaine = ((0.0, 0.0, 0.0), dimensions)
        self.scene.materiau_ambiant = self.cb_ambiant.currentText()
        self.scene.taille_maille_cao = self.spin_maille_cao.value()
        self._notifier(modifie=True)

    def _maj_nature(self, *_args):
        circuit = self.cb_nature.currentText() == "Circuit"
        self.groupe_primitive.setVisible(not circuit)
        self.groupe_circuit.setVisible(circuit)

    def _rotation(self):
        return (self.spin_rx.value(), self.spin_ry.value(), self.spin_rz.value())

    def _points_polyligne(self):
        points = []
        for bloc in self.edit_polyligne.text().split(";"):
            if bloc.strip():
                valeurs = [float(v.strip()) for v in bloc.split(",")]
                if len(valeurs) != 3:
                    raise ValueError("Chaque point de polyligne doit contenir x,y,z.")
                points.append(valeurs)
        if len(points) < 2:
            raise ValueError("Une polyligne exige au moins deux points.")
        return points

    def _construire_elements(self):
        centre = (self.spin_x.value(), self.spin_y.value(), self.spin_z.value())
        label = self.edit_label.text().strip() or "Objet"
        if self.cb_nature.currentText() == "Circuit":
            type_circuit = self.cb_circuit.currentText()
            return circuits_depuis_parametres(
                type_circuit, centre, courant=self.spin_courant.value(),
                rayon=self.spin_r.value(), longueur=self.spin_longueur.value(),
                n_spires=self.spin_spires.value(), rotation=self._rotation(),
                points=(self._points_polyligne()
                        if type_circuit == "polyligne" else None),
                label=label)
        role = self.cb_role.currentText()
        materiau = ("Cuivre" if role == "conducteur"
                    else self.cb_materiau.currentText()
                    if role == "materiau" else None)
        forme = self.cb_forme.currentText()
        if forme == "maillage_importe":
            raise ValueError("Utilisez le bouton « Importer STL / STEP ».")
        item = ItemGeometrie(
            forme,
            params_primitive(
                forme, centre,
                rayon=self.spin_r.value(),
                dimensions=(self.spin_dx.value(), self.spin_dy.value(),
                            self.spin_dz.value()),
                longueur=self.spin_longueur.value()),
            role=role,
            valeur=(self.spin_valeur.value() if role == "electrode" else None),
            materiau=materiau,
            q=(self.spin_q.value() if role == "source" else None),
            label=label, rotation=self._rotation(),
            operation_cao=self.cb_operation_cao.currentText())
        return [item]

    def importer_cao(self):
        chemin, _ = QFileDialog.getOpenFileName(
            self, "Importer un solide 3D", "",
            "Solides 3D (*.stl *.step *.stp);;STL (*.stl);;STEP (*.step *.stp)")
        if not chemin:
            return
        suffixe = Path(chemin).suffix.lower()
        operation = "domaine" if not self.scene.items_cao else "union"
        if suffixe == ".stl" and self.scene.items_cao:
            QMessageBox.warning(
                self, "STL discret",
                "Un STL peut former seul le domaine tétraédrique. Pour des "
                "booléens OpenCASCADE, importez un STEP.")
            operation = "aucune"
        item = ItemGeometrie(
            "maillage_importe",
            {"chemin": str(Path(chemin).resolve()), "format": suffixe[1:],
             "echelle": 1.0},
            role="decoratif", label=Path(chemin).stem,
            operation_cao=operation)
        self.scene.items.append(item)
        self.cb_operation_cao.setCurrentText(operation)
        self._rafraichir_liste(len(self.scene.items) - 1)
        self._notifier(modifie=True)

    def ajouter(self):
        try:
            elements = self._construire_elements()
            selection = -1
            for element in elements:
                if isinstance(element, ItemGeometrie):
                    self.scene.items.append(element)
                    selection = len(self.scene.items) - 1
                else:
                    self.scene.circuits.append(element)
                    selection = len(self.scene.items) + len(self.scene.circuits) - 1
            self._rafraichir_liste(selection)
            self._notifier(modifie=True)
        except (KeyError, TypeError, ValueError) as erreur:
            QMessageBox.warning(self, "Objet 3D invalide", str(erreur))

    def mettre_a_jour(self):
        index = self.index_selectionne
        if index < 0:
            return
        try:
            existant = (self.scene.items[index]
                        if index < len(self.scene.items) else None)
            if existant is not None and existant.forme == "maillage_importe":
                element = existant.dupliquer()
                element.identifiant = existant.identifiant
                element.label = self.edit_label.text().strip() or existant.label
                element.operation_cao = self.cb_operation_cao.currentText()
            else:
                element = self._construire_elements()[0]
            if index < len(self.scene.items):
                if not isinstance(element, ItemGeometrie):
                    raise ValueError("Conservez la nature Primitive pour cet objet.")
                element.identifiant = self.scene.items[index].identifiant
                self.scene.items[index] = element
            else:
                if isinstance(element, ItemGeometrie):
                    raise ValueError("Conservez la nature Circuit pour cet objet.")
                i = index - len(self.scene.items)
                element.identifiant = self.scene.circuits[i].identifiant
                self.scene.circuits[i] = element
            self._rafraichir_liste(index)
            self._notifier(modifie=True)
        except (KeyError, TypeError, ValueError) as erreur:
            QMessageBox.warning(self, "Modification impossible", str(erreur))

    def dupliquer(self):
        if self.index_selectionne < 0:
            return
        element = self.scene.dupliquer_element(self.index_selectionne)
        selection = (len(self.scene.items) - 1
                     if isinstance(element, ItemGeometrie)
                     else len(self.scene.items) + len(self.scene.circuits) - 1)
        self._rafraichir_liste(selection)
        self._notifier(modifie=True)

    def supprimer(self):
        index = self.index_selectionne
        if index < 0:
            return
        self.scene.supprimer_element(index)
        self._rafraichir_liste(min(index, len(self.scene.items) + len(self.scene.circuits) - 1))
        self._notifier(modifie=True)

    def sauvegarder(self):
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder la scène", "", "Scène FieldLab (*.json)")
        if chemin:
            try:
                self.scene.sauvegarder_json(chemin)
            except (OSError, TypeError, ValueError) as erreur:
                QMessageBox.critical(self, "Sauvegarde impossible", str(erreur))

    def charger(self):
        chemin, _ = QFileDialog.getOpenFileName(
            self, "Charger une scène", "", "Scène FieldLab (*.json)")
        if not chemin:
            return
        try:
            self.scene = Scene3D.charger_json(chemin)
            self._charger_domaine()
            self._rafraichir_liste(0 if self.scene.items or self.scene.circuits else -1)
            self._notifier(modifie=True)
        except (OSError, KeyError, TypeError, ValueError) as erreur:
            QMessageBox.critical(self, "Chargement impossible", str(erreur))

    def _charger_domaine(self):
        self._chargement_formulaire = True
        try:
            self.spin_lx.setValue(float(self.scene.dimensions[0]))
            self.spin_ly.setValue(float(self.scene.dimensions[1]))
            self.spin_lz.setValue(float(self.scene.dimensions[2]))
            self.cb_ambiant.setCurrentText(self.scene.materiau_ambiant)
            if self.scene.taille_maille_cao is not None:
                self.spin_maille_cao.setValue(self.scene.taille_maille_cao)
        finally:
            self._chargement_formulaire = False

    def _rafraichir_liste(self, selection=None):
        self.liste.blockSignals(True)
        self.liste.clear()
        for item in self.scene.items:
            suffixe = (f" — CAO: {item.operation_cao}"
                       if item.operation_cao != "aucune" else "")
            self.liste.addItem(item.libelle_legende() + suffixe)
        for circuit in self.scene.circuits:
            self.liste.addItem(
                f"{circuit.label} (circuit) — I={circuit.courant:g} A")
        if selection is not None and self.liste.count():
            self.liste.setCurrentRow(max(0, min(selection, self.liste.count() - 1)))
        self.liste.blockSignals(False)

    def selectionner_depuis_vue(self, index):
        if 0 <= index < self.liste.count():
            self.liste.setCurrentRow(index)

    def _remplacer_element(self, index, element):
        if index < len(self.scene.items):
            self.scene.items[index] = element
        else:
            self.scene.circuits[index - len(self.scene.items)] = element

    def appliquer_transformation_vue(
            self, index, nature, donnees, bornes_initiales):
        elements = self.scene.items + self.scene.circuits
        if not 0 <= index < len(elements):
            return
        try:
            if nature == "affine":
                m = np.asarray(donnees, dtype=float).reshape((4, 4))
                bornes = tuple(float(v) for v in bornes_initiales)
                centre0 = np.array([
                    (bornes[0] + bornes[1]) / 2,
                    (bornes[2] + bornes[3]) / 2,
                    (bornes[4] + bornes[5]) / 2,
                ])
                centre1 = m[:3, :3] @ centre0 + m[:3, 3]
                axes = self.cb_axes.currentText()
                for axe, lettre in enumerate("XYZ"):
                    if lettre not in axes:
                        centre1[axe] = centre0[axe]
                if self.chk_accrochage.isChecked():
                    pas = self.spin_pas_grille.value()
                    centre1 = np.round(centre1 / pas) * pas
                angles = list(angles_euler_depuis_matrice(m[:3, :3]))
                angles = [angle if lettre in axes else 0.0
                          for angle, lettre in zip(angles, "XYZ")]
                rotation = matrice_rotation_euler(angles)
                contrainte = np.eye(4)
                contrainte[:3, :3] = rotation
                contrainte[:3, 3] = centre1 - rotation @ centre0
                contrainte = contraindre_affine_dans_domaine(
                    contrainte, bornes, self.scene.bornes_vtk)
                element = transformer_element_affine(
                    elements[index], contrainte)
            elif nature == "bounds":
                element = self._redimensionner_element(
                    elements[index], donnees, bornes_initiales)
            else:
                return
            self._remplacer_element(index, element)
            self._rafraichir_liste(index)
            self._charger_selection(index)
            self._notifier(modifie=True)
        except (TypeError, ValueError, np.linalg.LinAlgError) as erreur:
            QMessageBox.warning(
                self, "Transformation impossible", str(erreur))

    def _redimensionner_element(self, element, nouvelles_bornes,
                                anciennes_bornes):
        nouveau = np.asarray(nouvelles_bornes, dtype=float)
        ancien = np.asarray(anciennes_bornes, dtype=float)
        nmin = nouveau[[0, 2, 4]].copy()
        nmax = nouveau[[1, 3, 5]].copy()
        amin = ancien[[0, 2, 4]]
        amax = ancien[[1, 3, 5]]
        axes = self.cb_axes.currentText()
        for axe, lettre in enumerate("XYZ"):
            if lettre not in axes:
                nmin[axe], nmax[axe] = amin[axe], amax[axe]
        pas = self.spin_pas_grille.value()
        if self.chk_accrochage.isChecked():
            centre = np.round(((nmin + nmax) / 2) / pas) * pas
            taille = np.maximum(
                np.round((nmax - nmin) / pas) * pas, pas)
            nmin, nmax = centre - taille / 2, centre + taille / 2
        d = np.asarray(self.scene.bornes_vtk, dtype=float)
        dmin, dmax = d[[0, 2, 4]], d[[1, 3, 5]]
        taille = np.minimum(np.maximum(nmax - nmin, 1e-9), dmax - dmin)
        centre = np.clip((nmin + nmax) / 2,
                         dmin + taille / 2, dmax - taille / 2)
        nmin, nmax = centre - taille / 2, centre + taille / 2
        ancienne_taille = np.maximum(amax - amin, 1e-12)
        rapports = taille / ancienne_taille
        ancien_centre = (amin + amax) / 2

        copie_element = copy.deepcopy(element)
        if isinstance(copie_element, ItemGeometrie):
            p = copie_element.params
            if copie_element.forme == "maillage_importe":
                facteur = float(np.cbrt(np.prod(rapports)))
                p["echelle"] = float(p.get("echelle", 1.0)) * facteur
                decalage = np.asarray(
                    p.get("decalage", (0.0, 0.0, 0.0)), dtype=float)
                p["decalage"] = (decalage + centre - ancien_centre).tolist()
                return copie_element
            centre_modele = centre_item(copie_element)
            if all(c in p for c in ("cx", "cy", "cz")):
                p.update(cx=float(centre[0]), cy=float(centre[1]),
                         cz=float(centre[2]))
            else:
                delta = centre - centre_modele
                for nom, valeur in zip(("x0", "y0", "z0"), delta):
                    p[nom] = float(p[nom] + valeur)
                for nom, valeur in zip(("x1", "y1", "z1"), delta):
                    p[nom] = float(p[nom] + valeur)
            if copie_element.forme == "boite":
                for nom, facteur in zip(("lx", "ly", "lz"), rapports):
                    if nom in p:
                        p[nom] = max(1e-9, float(p[nom]) * float(facteur))
            elif copie_element.forme == "sphere":
                p["r"] *= float(np.cbrt(np.prod(rapports)))
            elif copie_element.forme == "cylindre":
                axe = "xyz".index(p.get("axe", "z"))
                transverses = [i for i in range(3) if i != axe]
                p["longueur"] *= float(rapports[axe])
                p["r"] *= float(np.sqrt(
                    rapports[transverses[0]] * rapports[transverses[1]]))
            return copie_element


        copie_element.points = (
            (copie_element.points - ancien_centre) * rapports + centre)
        if "centre" in copie_element.params:
            copie_element.params["centre"] = centre.tolist()
        facteur = float(np.cbrt(np.prod(rapports)))
        if "rayon" in copie_element.params:
            copie_element.params["rayon"] *= facteur
        if "longueur" in copie_element.params:
            copie_element.params["longueur"] *= facteur
        return copie_element

    def _bornes_element(self, element):
        if not isinstance(element, ItemGeometrie):
            points = np.asarray(element.points, dtype=float)
            return points.min(axis=0), points.max(axis=0)
        if element.forme == "maillage_importe":
            return None
        p = element.params
        centre = centre_item(element)
        if element.forme == "sphere":
            demi = np.full(3, float(p["r"]))
        elif element.forme == "boite":
            demi = np.array([
                p.get("lx", p.get("x1", 0) - p.get("x0", 0)),
                p.get("ly", p.get("y1", 0) - p.get("y0", 0)),
                p.get("lz", p.get("z1", 0) - p.get("z0", 0)),
            ], dtype=float) / 2
        else:
            axe = "xyz".index(p.get("axe", "z"))
            demi = np.full(3, float(p["r"]))
            demi[axe] = float(p["longueur"]) / 2

        projection = np.abs(matrice_rotation_euler(element.rotation)) @ demi
        return centre - projection, centre + projection

    def _maj_diagnostic(self):
        avertissements = []
        dmin = np.asarray(self.scene.boite_domaine[0], dtype=float)
        dmax = np.asarray(self.scene.boite_domaine[1], dtype=float)
        bornes = []
        elements = self.scene.items + self.scene.circuits
        for i, element in enumerate(elements):
            b = self._bornes_element(element)
            bornes.append(b)
            if b is not None and (np.any(b[0] < dmin - 1e-9)
                                  or np.any(b[1] > dmax + 1e-9)):
                avertissements.append(f"{i + 1}: hors du domaine")
        for i in range(len(bornes)):
            if bornes[i] is None:
                continue
            for j in range(i + 1, len(bornes)):
                if bornes[j] is None:
                    continue
                recouvrement = np.minimum(bornes[i][1], bornes[j][1]) \
                    - np.maximum(bornes[i][0], bornes[j][0])
                if np.all(recouvrement > 1e-9):
                    avertissements.append(
                        f"{i + 1}↔{j + 1}: chevauchement à vérifier")
        if avertissements:
            self.label_diagnostic.setText(
                "Attention — " + " ; ".join(avertissements[:4]))
            self.label_diagnostic.setStyleSheet("color: #f59e0b;")
        else:
            self.label_diagnostic.setText(
                "Scène valide : tous les éléments connus sont dans le domaine.")
            self.label_diagnostic.setStyleSheet("color: #22c55e;")

    def _charger_selection(self, index):
        if index < 0:
            return
        self._chargement_formulaire = True
        try:
            if index < len(self.scene.items):
                item = self.scene.items[index]
                self.cb_nature.setCurrentText("Primitive")
                self.edit_label.setText(item.label)
                self.cb_forme.setCurrentText(item.forme)
                self.cb_role.setCurrentText(item.role)
                self.cb_operation_cao.setCurrentText(item.operation_cao)
                if item.materiau:
                    self.cb_materiau.setCurrentText(item.materiau)
                self.spin_valeur.setValue(float(item.valeur or 0.0))
                self.spin_q.setValue(float(item.q or 0.0))
                centre = (centre_item(item) if item.forme != "maillage_importe"
                          else np.asarray(item.params.get("centre", (0, 0, 0)), float))
                p = item.params
                self.spin_r.setValue(float(p.get("r", self.spin_r.value())))
                self.spin_dx.setValue(float(p.get("lx", p.get("x1", 0) - p.get("x0", -0.2))))
                self.spin_dy.setValue(float(p.get("ly", p.get("y1", 0) - p.get("y0", -0.2))))
                self.spin_dz.setValue(float(p.get("lz", p.get("z1", 0) - p.get("z0", -0.2))))
                self.spin_longueur.setValue(float(p.get("longueur", self.spin_longueur.value())))
                rotation = item.rotation
            else:
                circuit = self.scene.circuits[index - len(self.scene.items)]
                self.cb_nature.setCurrentText("Circuit")
                self.edit_label.setText(circuit.label)
                self.cb_circuit.setCurrentText(circuit.type_circuit)
                self.spin_courant.setValue(circuit.courant)
                p = circuit.params
                centre = np.asarray(p.get("centre", circuit.points.mean(axis=0)))
                self.spin_r.setValue(float(p.get("rayon", self.spin_r.value())))
                self.spin_longueur.setValue(float(p.get("longueur", self.spin_longueur.value())))
                self.spin_spires.setValue(int(p.get("n_spires", self.spin_spires.value())))
                rotation = p.get("rotation", (0.0, 0.0, 0.0))
                if circuit.type_circuit == "polyligne":
                    self.edit_polyligne.setText("; ".join(
                        ",".join(f"{v:g}" for v in point)
                        for point in circuit.points))
            self.spin_x.setValue(float(centre[0]))
            self.spin_y.setValue(float(centre[1]))
            self.spin_z.setValue(float(centre[2]))
            self.spin_rx.setValue(float(rotation[0]))
            self.spin_ry.setValue(float(rotation[1]))
            self.spin_rz.setValue(float(rotation[2]))
        finally:
            self._chargement_formulaire = False
        self._notifier(modifie=False)

    def _notifier(self, modifie=False):
        if modifie:
            self._enregistrer_historique()
        self._maj_diagnostic()
        if not self._chargement_formulaire and self.callback_scene is not None:
            self.callback_scene(
                self.scene, self.index_selectionne, bool(modifie))
