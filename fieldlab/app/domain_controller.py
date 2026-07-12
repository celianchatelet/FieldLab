import copy
import queue
import threading

import numpy as np
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

from fieldlab.annulation import CalculAnnule
from fieldlab.garde_fous import verifier_parametres
from fieldlab import geometries as geo
from fieldlab.solvers import solve
from fieldlab.app.panels.electrostatique import ElectrostatiquePanel
from fieldlab.app.panels.magneto import MagnetoPanel
from fieldlab.app.panels.thermique import ThermiquePanel
from fieldlab.app.plot_panel import PlotPanel


_PANEL_CLS = {
    "Electrostatique":  ElectrostatiquePanel,
    "Magnetostatique":  MagnetoPanel,
    "Thermique":        ThermiquePanel,
}


class DomainController(QObject):
    def __init__(self, domaine, parent=None):
        super().__init__(parent)
        self.domaine = domaine
        self.result = None
        self._derniers_parametres = None
        self._reference = None
        self._queue = queue.Queue()




        self._generation = 0





        self._annulation = threading.Event()

        panel_cls = _PANEL_CLS.get(domaine.nom, ElectrostatiquePanel)
        self.panel = panel_cls(controller=self)
        self.plot = PlotPanel(domaine)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(100)
        self.panel._scene_2d_modifiee()
        self.panel.status.setText("Prêt — définissez la scène puis lancez la simulation.")

    def run_simulation(self):
        try:
            p = self.panel.read_params()
        except ValueError as e:
            QMessageBox.critical(self.panel, "Paramètres invalides", str(e))
            return



        bloquants, avertissements = verifier_parametres(p, self.domaine.nom)
        if bloquants:
            QMessageBox.critical(
                self.panel, "Paramètres incompatibles",
                "\n\n".join(bloquants))
            return
        if avertissements:
            reponse = QMessageBox.question(
                self.panel, "Calcul potentiellement lourd",
                "\n\n".join(avertissements) + "\n\nLancer quand même ?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reponse != QMessageBox.StandardButton.Yes:
                return



        self._annulation.set()
        annulation = threading.Event()
        self._annulation = annulation
        champ0_3d = None
        constructeur_3d = None
        if p.get("dimension") == "3D":
            try:
                preparation = self._preparer_construction_3d(
                    p, annule=annulation.is_set)
            except Exception as e:
                QMessageBox.critical(self.panel, "Erreur de simulation", str(e))
                return
            differable = (
                self.domaine.nom == "Magnetostatique"
                or getattr(preparation[0],
                           "constructible_hors_thread_principal", False))
            if differable:






                p = dict(p)
                if "scene_3d" in p:
                    p["scene_3d"] = copy.deepcopy(p["scene_3d"])
                construire, kwargs_3d, accepte_scene = preparation
                if "scene" in kwargs_3d:
                    kwargs_3d = dict(kwargs_3d)
                    kwargs_3d["scene"] = p["scene_3d"]
                constructeur_3d = (construire, kwargs_3d, accepte_scene)
            else:










                try:
                    champ0_3d = self._construire_champ0_3d(preparation, p)
                except Exception as e:
                    QMessageBox.critical(self.panel, "Erreur de simulation", str(e))
                    return
        self.panel.set_running(True)
        self.panel.status.setText("Calcul en cours...")
        self.panel.progress.setValue(0)
        self._generation += 1
        self._derniers_parametres = copy.deepcopy(p)
        threading.Thread(
            target=self._worker,
            args=(p, self._generation, champ0_3d, constructeur_3d,
                  annulation),
            daemon=True).start()

    def _preparer_construction_3d(self, p, annule=None):
        construire = self.panel.SCENARIOS_3D[p["geom_3d"]]
        kwargs_3d = {"n": p["N_3d"]}
        if "taille_m_3d" in p:
            kwargs_3d["taille_m"] = p["taille_m_3d"]
        if "walls_3d" in p:
            kwargs_3d["walls"] = p["walls_3d"]
        if "obstacles_3d" in p:
            kwargs_3d["obstacles"] = p["obstacles_3d"]
        if annule is not None and self.panel._scenario_3d_accepte("annule"):
            kwargs_3d["annule"] = annule




        if "v" in p:
            for nom_amplitude in ("v", "t_chaud", "amplitude"):
                if self.panel._scenario_3d_accepte(nom_amplitude):
                    kwargs_3d[nom_amplitude] = float(p["v"])






        dynamiques = {
            "T_initiale": p.get("T_initiale_3d"),
            "duree": p.get("duree_3d"),
            "n_images": p.get("n_images_3d"),
            "forme": p.get("forme_temporelle_3d"),
            "frequence": p.get("frequence_3d"),
        }
        if dynamiques["duree"] and dynamiques["n_images"]:
            dynamiques["dt"] = (float(dynamiques["duree"])
                                / max(1, int(dynamiques["n_images"]) * 5))
        for nom, valeur in dynamiques.items():
            if valeur is None or not self.panel._scenario_3d_accepte(nom):
                continue
            if nom == "forme":
                kwargs_3d[nom] = str(valeur)
            elif nom == "n_images":
                kwargs_3d[nom] = int(valeur)
            else:
                kwargs_3d[nom] = float(valeur)
        accepte_scene = self.panel._scenario_3d_accepte("scene")
        if accepte_scene and "scene_3d" in p:
            kwargs_3d["scene"] = p["scene_3d"]
        return construire, kwargs_3d, accepte_scene

    def _construire_champ0_3d(self, preparation, p):
        construire, kwargs_3d, accepte_scene = preparation
        champ0 = construire(**kwargs_3d)
        return champ0

    def _worker(self, p, gen, champ0_3d=None, constructeur_3d=None,
                annulation=None):
        annule = annulation.is_set if annulation is not None else None
        try:
            if p.get("dimension") == "3D":
                if champ0_3d is None and constructeur_3d is not None:



                    self._queue.put(("progress", (5, gen)))
                    champ0_3d = self._construire_champ0_3d(constructeur_3d, p)






                res = self._resoudre_3d(
                    champ0_3d, gen, annule=annule, parametres=p)
                self._queue.put((
                    "done", (res, p["viz"], p.get("scalaire_3d"), gen)))
                return

            regime = p.get("regime", "Stationnaire")

            if regime == "Variable":




                from fieldlab.regime_variable import resoudre_regime_variable
                n_images = p["n_images"]

                def prog(it, err):
                    self._queue.put(("progress", (min(100, 100 * it / (n_images + 1)), gen)))

                res = resoudre_regime_variable(
                    self.domaine.scenarios, p["geom"], p["N"], p["v"],
                    p["forme_temporelle"], p["frequence"], p["walls"], p["obstacles"],
                    p["method"], p["omega"], p["tol"], p["max_iter"], p.get("refine", 0),
                    p["duree"], n_images, kappa_fond=p.get("kappa_fond", 1.0),
                    taille_domaine=p.get("taille_domaine", 1.0), progress=prog,
                    annule=annule)
            else:
                q = p.get("q")
                field = geo.build(self.domaine.scenarios, p["geom"], p["N"], p["v"],
                                   p["walls"], p["obstacles"], q=q,
                                   kappa_fond=p.get("kappa_fond", 1.0),
                                   taille_domaine=p.get("taille_domaine", 1.0),
                                   rho_cp_fond=p.get("rho_cp_fond", 1.0))

                if regime == "Transitoire":


                    from fieldlab.fem.transient import resoudre_transitoire
                    n_images = p["n_images"]
                    duree = p["duree"]
                    dt = duree / max(1, n_images * 5)
                    n_pas_estime = max(1, round(duree / dt))

                    def prog(it, err):
                        self._queue.put(("progress", (min(100, 100 * it / n_pas_estime), gen)))

                    res = resoudre_transitoire(field, T_initiale=p["T_initiale"], dt=dt,
                                                duree=duree, n_images=n_images,
                                                refine=p.get("refine", 0), progress=prog,
                                                annule=annule)
                else:
                    def prog(it, err):
                        self._queue.put(("progress", (min(100, 100 * it / p["max_iter"]), gen)))

                    res = solve(field, p["method"], omega=p["omega"], tol=p["tol"],
                                max_iter=p["max_iter"], progress=prog,
                                refine=p.get("refine", 0), annule=annule)
            self._queue.put(("done", (res, p["viz"], None, gen)))
        except CalculAnnule:
            self._queue.put(("cancelled", gen))
        except Exception as e:
            self._queue.put(("error", (str(e), gen)))


    def _resoudre_3d(self, champ0, gen, annule=None, parametres=None):
        from fieldlab.fem3d.field3d import Field3D
        from fieldlab.fem3d.poisson import solve_poisson_3d

        if not isinstance(champ0, Field3D):
            return champ0
        p = parametres or {}
        if (self.domaine.nom == "Thermique"
                and p.get("regime_3d") == "Transitoire"):
            from fieldlab.fem3d.transient import resoudre_transitoire_3d
            duree = float(p.get("duree_3d", 3.0))
            n_images = int(p.get("n_images_3d", 30))
            dt = duree / max(1, n_images * 5)
            n_pas = max(1, int(round(duree / dt)))

            def progression(it, _err):
                self._queue.put((
                    "progress", (min(100, 100 * it / n_pas), gen)))

            return resoudre_transitoire_3d(
                champ0,
                T_initiale=float(p.get("T_initiale_3d", 0.0)),
                dt=dt,
                duree=duree,
                n_images=n_images,
                progress=progression,
                annule=annule)
        ancrage_paroi = any(
            spec and spec[0] in ("robin", "radiation")
            for spec in champ0.walls.values())
        if not np.any(champ0.fixed_mask) and not ancrage_paroi:
            raise ValueError(
                "La scène 3D n'a aucune valeur imposée : ajoutez au moins "
                "une électrode/température imposée, ou une paroi de "
                "convection, avant de résoudre.")

        def prog(_it, _err):
            self._queue.put(("progress", (50, gen)))

        self._queue.put(("progress", (10, gen)))
        return solve_poisson_3d(
            champ0, methode="direct", progress=prog, annule=annule)

    def _poll(self):
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "progress":
                    valeur, gen = payload
                    if gen != self._generation:
                        continue
                    self.panel.progress.setValue(int(valeur))
                elif kind == "done":
                    res, vizkind, scalaire_3d, gen = payload
                    if gen != self._generation:
                        continue
                    self.result = res
                    self.panel.progress.setValue(100)
                    if hasattr(res, "champs"):
                        msg = (f"Régime temporel : {len(res.champs)} images, "
                               f"{res.instants[-1]:.3g} s simulées "
                               f"(calcul en {res.temps:.2f} s)")
                        if not res.converge:
                            msg += " — ATTENTION : au moins un instant n'a pas convergé"
                    else:
                        msg = (f"Convergé en {res.iterations} itér. "
                               f"({res.temps:.2f} s, err={res.erreur:.1e})"
                               if res.converge else
                               f"NON convergé ({res.iterations} itér.)")
                    self.panel.status.setText(msg)
                    self.panel.set_running(False)
                    if scalaire_3d is not None:
                        self.plot.set_scalaire_3d(scalaire_3d)
                    self.plot.redraw(self.result, vizkind)
                elif kind == "error":
                    message, gen = payload
                    if gen != self._generation:
                        continue
                    QMessageBox.critical(self.panel, "Erreur de simulation", message)
                    self.panel.status.setText("Erreur.")
                    self.panel.set_running(False)
                elif kind == "cancelled":
                    gen = payload
                    if gen != self._generation:
                        continue
                    self.panel.status.setText("Calcul annulé.")
                    self.panel.set_running(False)
        except queue.Empty:
            pass

    def refresh_plot(self, kind):
        if self.result is not None:
            self.plot.redraw(self.result, kind)

    def reinitialiser(self):
        self._annulation.set()
        self._generation += 1
        self.panel._vider_obstacles()
        self.result = None
        self.panel.progress.setValue(0)
        self.panel.status.setText("Prêt.")
        self.panel.set_running(False)
        self.plot.reset()
        self.panel._scene_2d_modifiee()
        self.panel.status.setText("Prêt — définissez la scène puis lancez la simulation.")

    def reinitialiser_resultat_seul(self):
        self._annulation.set()
        self._generation += 1
        self.result = None
        self._derniers_parametres = None
        self.panel.progress.setValue(0)
        self.panel.status.setText("Configuration chargée — prêt à calculer.")
        self.panel.set_running(False)
        self.plot.reset()
        self.panel._scene_2d_modifiee()
        self.panel.status.setText("Configuration chargée — prête à calculer.")

    def annuler(self):
        if self._annulation.is_set():
            return
        self._annulation.set()
        self.panel.set_cancelling()
        self.panel.status.setText("Annulation demandée…")

    def export_png(self, parent=None):
        if self.result is None:
            QMessageBox.information(parent, "Rien a exporter",
                                     "Lancez d'abord une simulation.")
            return
        path, _ = QFileDialog.getSaveFileName(parent, "Exporter la figure", "",
                                               "PNG (*.png)")
        if path:
            self.plot.save_png(path)
            self.panel.status.setText(f"Figure exportée : {path}")

    def export_csv(self, parent=None):
        champ = self.plot.champ_affiche()
        if champ is None:
            QMessageBox.information(parent, "Rien a exporter",
                                     "Lancez d'abord une simulation.")
            return
        path, _ = QFileDialog.getSaveFileName(parent, "Exporter le champ", "",
                                               "CSV (*.csv)")
        if not path:
            return
        from fieldlab.export import exporter_csv
        exporter_csv(
            path, champ, self.domaine, self._metadonnees())
        self.panel.status.setText(f"Champ exporté : {path}")

    def export_rapport(self, parent=None):
        if self.result is None:
            QMessageBox.information(
                parent, "Rien à exporter",
                "Lancez d'abord une simulation.")
            return
        path, _ = QFileDialog.getSaveFileName(
            parent, "Exporter le rapport pédagogique", "",
            "Rapport HTML (*.html)")
        if not path:
            return
        from fieldlab.export import exporter_rapport_html
        try:
            exporter_rapport_html(
                path,
                self._metadonnees(),
                self.plot.image_png())
            self.panel.status.setText(f"Rapport exporté : {path}")
        except (OSError, RuntimeError, TypeError, ValueError) as erreur:
            QMessageBox.critical(parent, "Erreur d'export", str(erreur))
            self.panel.status.setText("Erreur d'export.")

    def _metadonnees(self):
        from fieldlab.export import metadonnees_calcul
        meta = metadonnees_calcul(
            self.domaine, self._derniers_parametres, self.result)
        meta["hypotheses_et_limites"] = self.panel.label_validite.text()
        return meta

    @staticmethod
    def _texte_indicateurs(titre, valeurs):
        lignes = [titre, ""]
        for nom, valeur in valeurs.items():
            libelle = nom.replace("_", " ").capitalize()
            lignes.append(
                f"{libelle} : {valeur:.6g}" if isinstance(valeur, float)
                else f"{libelle} : {valeur}")
        return "\n".join(lignes)

    def afficher_analyse(self, parent=None):
        champ = self.plot.champ_affiche()
        if champ is None:
            QMessageBox.information(
                parent, "Analyse indisponible",
                "Lancez d'abord une simulation.")
            return
        from fieldlab.analyse import resumer_champ
        valeurs = resumer_champ(champ, self.domaine)
        QMessageBox.information(
            parent, "Indicateurs physiques",
            self._texte_indicateurs(
                f"{self.domaine.titre} — {self.domaine.scalaire}", valeurs))

    def memoriser_reference(self, parent=None):
        champ = self.plot.champ_affiche()
        if champ is None:
            QMessageBox.information(
                parent, "Référence indisponible",
                "Lancez d'abord une simulation.")
            return
        self._reference = champ.copy()
        self.panel.status.setText(
            "Résultat mémorisé comme référence A.")

    def comparer_reference(self, parent=None):
        champ = self.plot.champ_affiche()
        if champ is None or self._reference is None:
            QMessageBox.information(
                parent, "Comparaison indisponible",
                "Mémorisez d'abord un résultat A, puis lancez le résultat B.")
            return
        from fieldlab.analyse import comparer_champs
        try:
            valeurs = comparer_champs(self._reference, champ)
        except ValueError as erreur:
            QMessageBox.warning(parent, "Comparaison impossible", str(erreur))
            return
        QMessageBox.information(
            parent, "Comparaison A/B",
            self._texte_indicateurs(
                "Écart entre la référence A et le résultat courant B", valeurs))

    def export_video(self, parent=None):
        if self.plot._transitoire is None:
            QMessageBox.information(
                parent, "Rien a exporter",
                "Aucune animation active : lancez d'abord une simulation en "
                "regime transitoire (thermique) ou variable (electro/magneto).")
            return
        path, _ = QFileDialog.getSaveFileName(
            parent, "Exporter l'animation", "",
            "Video MP4 (*.mp4);;Animation GIF (*.gif)")
        if not path:
            return
        self.panel.status.setText("Export de l'animation en cours...")
        try:
            self.plot.export_video(path)
            self.panel.status.setText(f"Animation exportée : {path}")
        except Exception as e:
            QMessageBox.critical(parent, "Erreur d'export", str(e))
            self.panel.status.setText("Erreur d'export.")
