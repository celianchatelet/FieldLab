from __future__ import annotations

import base64
import csv
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path

import numpy as np

from fieldlab.unites import format_duree


def _jsonable(objet):
    if isinstance(objet, np.ndarray):
        return objet.tolist()
    if isinstance(objet, np.generic):
        return objet.item()
    if hasattr(objet, "to_dict"):
        return _jsonable(objet.to_dict())
    if isinstance(objet, dict):
        return {str(k): _jsonable(v) for k, v in objet.items()}
    if isinstance(objet, (list, tuple)):
        return [_jsonable(v) for v in objet]
    if isinstance(objet, (str, int, float, bool)) or objet is None:
        return objet
    return str(objet)


def metadonnees_calcul(domaine, parametres, resultat) -> dict:
    parametres_export = _jsonable(parametres or {})
    for cle in ("duree", "duree_3d"):
        if cle in parametres_export:
            parametres_export[f"{cle}_formatee"] = format_duree(
                parametres_export[cle])
    meta = {
        "format": "fieldlab-resultat",
        "version": 1,
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "domaine": domaine.nom,
        "titre": domaine.titre,
        "scalaire": domaine.scalaire,
        "champ_vectoriel": domaine.champ,
        "parametres": parametres_export,
    }
    if resultat is not None:
        meta["calcul"] = {
            "iterations": getattr(resultat, "iterations", None),
            "residu_relatif": getattr(resultat, "erreur", None),
            "temps_s": getattr(resultat, "temps", None),
            "converge": getattr(resultat, "converge", None),
            "nombre_images": len(getattr(resultat, "champs", []) or []),
        }
        instants = getattr(resultat, "instants", None)
        if instants:
            meta["calcul"]["duree_simulee_s"] = float(instants[-1])
            meta["calcul"]["duree_simulee_formatee"] = format_duree(
                instants[-1])
    return _jsonable(meta)


def exporter_csv(chemin, champ, domaine, metadonnees=None) -> None:
    from fieldlab.fem3d.field3d import Field3D

    nom_source = {
        "Electrostatique": "densite_charge_C_m3",
        "Magnetostatique": "densite_courant_A_m2",
        "Thermique": "source_thermique_W_m3",
    }.get(domaine.nom, "source")

    chemin = Path(chemin)
    if isinstance(champ, Field3D):
        colonnes = [
            ("x_m", champ.mesh.p[0]),
            ("y_m", champ.mesh.p[1]),
            ("z_m", champ.mesh.p[2]),
            ("scalaire", champ.V),
        ]
        if champ.vecteurs is not None:
            colonnes += [
                ("champ_x", champ.vecteurs[:, 0]),
                ("champ_y", champ.vecteurs[:, 1]),
                ("champ_z", champ.vecteurs[:, 2]),
                ("champ_norme", np.linalg.norm(champ.vecteurs, axis=1)),
            ]
        colonnes += [
            ("valeur_imposee", champ.fixed_mask.astype(int)),
            ("isolant", champ.solid_mask.astype(int)),
            ("kappa", champ.kappa),
            (nom_source, champ.source),
            ("rho_cp_J_m3_K", champ.rho_cp),
        ]
    else:
        ny, nx = champ.V.shape
        longueur = float(getattr(champ, "taille_domaine", 1.0))
        x, y = np.meshgrid(
            np.linspace(0.0, longueur, nx),
            np.linspace(0.0, longueur, ny))
        vx, vy, norme = domaine.champ_fn(champ)
        colonnes = [
            ("x_m", x.ravel()),
            ("y_m", y.ravel()),
            ("scalaire", champ.V.ravel()),
            ("champ_x", np.asarray(vx).ravel()),
            ("champ_y", np.asarray(vy).ravel()),
            ("champ_norme", np.asarray(norme).ravel()),
            ("valeur_imposee", champ.fixed_mask.astype(int).ravel()),
            ("isolant", champ.solid_mask.astype(int).ravel()),
            ("kappa", champ.kappa.ravel()),
            (nom_source, champ.source.ravel()),
            ("rho_cp_J_m3_K", champ.rho_cp.ravel()),
        ]

    with chemin.open("w", encoding="utf-8", newline="") as fichier:
        if metadonnees:
            fichier.write("# metadata=" + json.dumps(
                _jsonable(metadonnees), ensure_ascii=False,
                separators=(",", ":")) + "\n")
        fichier.write(
            f"# scalaire={domaine.scalaire}; champ={domaine.champ}\n")
        writer = csv.writer(fichier)
        writer.writerow([nom for nom, _valeurs in colonnes])
        writer.writerows(zip(*(np.asarray(v).tolist() for _n, v in colonnes)))


def exporter_rapport_html(chemin, metadonnees, image_png=None) -> None:
    meta = _jsonable(metadonnees or {})
    calcul = meta.get("calcul", {})
    params = meta.get("parametres", {})
    image = ""
    if image_png:
        donnees = base64.b64encode(image_png).decode("ascii")
        image = (f'<img alt="Visualisation FieldLab" '
                 f'src="data:image/png;base64,{donnees}">')
    lignes_calcul = "".join(
        f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>"
        for k, v in calcul.items())
    parametres = escape(json.dumps(params, ensure_ascii=False, indent=2))
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>Rapport FieldLab — {escape(str(meta.get('titre', 'Simulation')))}</title>
<style>
body{{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#172033}}
h1,h2{{color:#14213d}} table{{border-collapse:collapse}} th,td{{border:1px solid #ccd5e0;padding:.45rem;text-align:left}}
th{{background:#eef3f8}} img{{max-width:100%;border:1px solid #ccd5e0;border-radius:8px}}
pre{{white-space:pre-wrap;background:#f5f7fa;padding:1rem;border-radius:8px}} .note{{color:#53657d}}
</style></head><body>
<h1>Rapport de simulation FieldLab</h1>
<p><strong>Domaine :</strong> {escape(str(meta.get('titre', '')))}<br>
<strong>Grandeur :</strong> {escape(str(meta.get('scalaire', '')))}<br>
<strong>Champ :</strong> {escape(str(meta.get('champ_vectoriel', '')))}</p>
{image}
<h2>Diagnostic numérique</h2><table>{lignes_calcul}</table>
<h2>Configuration reproductible</h2><pre>{parametres}</pre>
<p class="note">Les propriétés de matériaux et modèles simplifiés de FieldLab
sont destinés à l'enseignement. Vérifier le panneau « Cadre scientifique et
limites » avant toute interprétation d'ingénierie.</p>
</body></html>"""
    Path(chemin).write_text(html, encoding="utf-8")
