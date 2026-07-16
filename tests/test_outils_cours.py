from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure
from PIL import Image

from fieldlab.app.plot_panel import PlotPanel
from fieldlab.grid import Field


def test_echantillonnage_sonde_2d_est_bilineaire_en_coordonnees_metres():
    n, longueur = 11, 2.0
    x = np.linspace(0.0, longueur, n)
    y = np.linspace(0.0, longueur, n)
    X, Y = np.meshgrid(x, y)
    champ = Field(
        2.0 * X + 3.0 * Y, np.zeros((n, n), dtype=bool),
        h=longueur / (n - 1), taille_domaine=longueur)
    valeur = PlotPanel._echantillonner_2d(champ, 0.73, 1.19)
    assert np.isclose(valeur, 2.0 * 0.73 + 3.0 * 1.19)


def test_horodatage_est_incruste_dans_image_rgb():
    image = np.full((180, 320, 3), 255, dtype=np.uint8)
    annotee = PlotPanel._incruster_horodatage(image, 8100.0)
    assert annotee.shape == image.shape
    assert np.any(annotee[:60, :180] != 255)


def test_export_png_1080p_a_la_resolution_demandee(tmp_path):
    figure = Figure(figsize=(4, 3), dpi=100)
    axe = figure.add_subplot(111)
    axe.plot([0, 1], [0, 1])
    faux_plot = SimpleNamespace(
        btn_3d=SimpleNamespace(isChecked=lambda: False),
        figure=figure,
        canvas=SimpleNamespace(draw_idle=lambda: None),
        _styler_figure=lambda _figure: None,
    )
    chemin = tmp_path / "cours.png"
    PlotPanel.save_png(
        faux_plot, chemin, resolution="1080p", fond="blanc",
        titre="Validation")
    with Image.open(chemin) as image:
        assert image.size == (1920, 1080)
