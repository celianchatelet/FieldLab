from PySide6.QtGui import QColor, QPalette

_STYLE_SHEET = """
QGroupBox {
    font-weight: 600;
    border: 1px solid palette(mid);
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QDockWidget::title {
    padding: 6px;
    font-weight: 600;
}
QPushButton:checked {
    background-color: palette(highlight);
    color: palette(highlighted-text);
    border: 1px solid palette(highlight);
    border-radius: 3px;
    padding: 3px 8px;
}
QToolTip {
    color: palette(text);
    background-color: palette(base);
    border: 1px solid palette(mid);
}
"""


_SOMBRE = False


_FOND = "#0b1020"
_PANNEAU = "#151b2b"
_BORDURE = "#2a3448"
_TEXTE = "#e6edf7"
_TEXTE_SECONDAIRE = "#9aa7bd"
_ACCENT = "#38bdf8"
_SELECTION = "#f59e0b"
_ERREUR = "#f87171"
_SUCCES = "#4ade80"


def est_sombre() -> bool:
    return _SOMBRE


def couleurs(sombre: bool = None) -> dict:
    if sombre is None:
        sombre = _SOMBRE
    if sombre:
        return {
            "fond": _FOND,
            "panneau": _PANNEAU,
            "bordure": _BORDURE,
            "fond_vtk": "#10162a",
            "texte": _TEXTE,
            "texte_secondaire": _TEXTE_SECONDAIRE,
            "grille": _BORDURE,
            "accent": _ACCENT,
            "selection": _SELECTION,
            "erreur": _ERREUR,
            "succes": _SUCCES,
        }
    return {
        "fond": "#ffffff",
        "panneau": "#f4f6fa",
        "bordure": "#d1d5db",
        "fond_vtk": "white",
        "texte": "#111827",
        "texte_secondaire": "#6b7280",
        "grille": "#d1d5db",
        "accent": "#2563eb",
        "selection": "#d97706",
        "erreur": "#dc2626",
        "succes": "#16a34a",
    }


def _light_palette():
    return QPalette()


def _dark_palette():
    p = QPalette()
    fond = QColor(_FOND)
    panneau = QColor(_PANNEAU)
    bordure = QColor(_BORDURE)
    texte = QColor(_TEXTE)
    secondaire = QColor(_TEXTE_SECONDAIRE)
    accent = QColor(_ACCENT)

    p.setColor(QPalette.ColorRole.Window, fond)
    p.setColor(QPalette.ColorRole.WindowText, texte)
    p.setColor(QPalette.ColorRole.Base, panneau)
    p.setColor(QPalette.ColorRole.AlternateBase, QColor("#10162a"))
    p.setColor(QPalette.ColorRole.ToolTipBase, panneau)
    p.setColor(QPalette.ColorRole.ToolTipText, texte)
    p.setColor(QPalette.ColorRole.Text, texte)
    p.setColor(QPalette.ColorRole.PlaceholderText, secondaire)
    p.setColor(QPalette.ColorRole.Button, QColor("#1b2336"))
    p.setColor(QPalette.ColorRole.ButtonText, texte)
    p.setColor(QPalette.ColorRole.BrightText, QColor(_ERREUR))
    p.setColor(QPalette.ColorRole.Light, bordure)
    p.setColor(QPalette.ColorRole.Midlight, bordure)
    p.setColor(QPalette.ColorRole.Mid, bordure)
    p.setColor(QPalette.ColorRole.Dark, QColor("#080d19"))
    p.setColor(QPalette.ColorRole.Shadow, QColor("#05080f"))
    p.setColor(QPalette.ColorRole.Link, accent)
    p.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText,
                 QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor("#5d6b82"))
    return p


def apply_theme(app, dark: bool):
    global _SOMBRE
    _SOMBRE = bool(dark)
    app.setStyle("Fusion")
    app.setPalette(_dark_palette() if dark else _light_palette())
    app.setStyleSheet(_STYLE_SHEET)
