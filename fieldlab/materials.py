from dataclasses import dataclass


KAPPA_VIDE = 1.0


_KAPPA_CONDUCTEUR_ELEC = 1.0e4


@dataclass(frozen=True)
class Material:
    nom: str
    kappa_thermique: float
    kappa_electrique: float
    kappa_magnetique: float
    masse_volumique: float = 1000.0
    capacite_thermique: float = 1000.0
    description: str = ""

    @property
    def rho_cp(self) -> float:
        return self.masse_volumique * self.capacite_thermique


MATERIAUX: dict[str, Material] = {
    "Cuivre": Material(
        "Cuivre", kappa_thermique=400.0, kappa_electrique=_KAPPA_CONDUCTEUR_ELEC,
        kappa_magnetique=1.0,
        masse_volumique=8960.0, capacite_thermique=385.0,
        description="Excellent conducteur thermique et electrique, amagnetique."),
    "Aluminium": Material(
        "Aluminium", kappa_thermique=237.0, kappa_electrique=_KAPPA_CONDUCTEUR_ELEC,
        kappa_magnetique=1.0,
        masse_volumique=2700.0, capacite_thermique=897.0,
        description="Bon conducteur, leger, amagnetique."),
    "Acier": Material(
        "Acier", kappa_thermique=50.0, kappa_electrique=_KAPPA_CONDUCTEUR_ELEC,
        kappa_magnetique=1.0 / 1000.0,
        masse_volumique=7850.0, capacite_thermique=490.0,
        description="Conducteur, ferromagnetique (concentre le champ B)."),
    "Fer": Material(
        "Fer", kappa_thermique=80.0, kappa_electrique=_KAPPA_CONDUCTEUR_ELEC,
        kappa_magnetique=1.0 / 5000.0,
        masse_volumique=7870.0, capacite_thermique=449.0,
        description="Conducteur, tres fortement ferromagnetique."),
    "Silicium": Material(
        "Silicium", kappa_thermique=150.0, kappa_electrique=11.7,
        kappa_magnetique=1.0,
        masse_volumique=2330.0, capacite_thermique=705.0,
        description="Semi-conducteur, bon conducteur thermique, amagnetique."),
    "Verre": Material(
        "Verre", kappa_thermique=1.0, kappa_electrique=7.0,
        kappa_magnetique=1.0,
        masse_volumique=2500.0, capacite_thermique=840.0,
        description="Isolant electrique et thermique modere, dielectrique."),
    "Plastique": Material(
        "Plastique", kappa_thermique=0.2, kappa_electrique=3.0,
        kappa_magnetique=1.0,
        masse_volumique=1200.0, capacite_thermique=1500.0,
        description="Bon isolant thermique et electrique."),
    "Ceramique": Material(
        "Ceramique", kappa_thermique=30.0, kappa_electrique=9.0,
        kappa_magnetique=1.0,
        masse_volumique=3800.0, capacite_thermique=850.0,
        description="Bon conducteur thermique mais isolant electrique."),
    "Eau": Material(
        "Eau", kappa_thermique=0.6, kappa_electrique=80.0,
        kappa_magnetique=1.0,
        masse_volumique=1000.0, capacite_thermique=4186.0,
        description="Isolant thermique modere, tres fort dielectrique."),
    "Huile": Material(
        "Huile", kappa_thermique=0.13, kappa_electrique=2.2,
        kappa_magnetique=1.0,
        masse_volumique=900.0, capacite_thermique=1900.0,
        description="Huile mineral/isolante (type huile de transformateur) : "
                     "isolant thermique et electrique, amagnetique."),
    "Air": Material(
        "Air", kappa_thermique=0.026, kappa_electrique=1.0006,
        kappa_magnetique=1.0,
        masse_volumique=1.2, capacite_thermique=1005.0,
        description="Tres bon isolant thermique, dielectrique quasi parfait."),
    "Vide": Material(
        "Vide", kappa_thermique=1.0e-6, kappa_electrique=KAPPA_VIDE,
        kappa_magnetique=1.0,
        masse_volumique=1.0e-6, capacite_thermique=1.0,
        description="Aucune conduction thermique ; reference electromagnetique."),
}

NOMS_MATERIAUX = list(MATERIAUX)


def kappa_pour_domaine(materiau: Material, domaine_nom: str) -> float:
    if domaine_nom == "Thermique":
        return materiau.kappa_thermique
    if domaine_nom == "Electrostatique":
        return materiau.kappa_electrique
    if domaine_nom == "Magnetostatique":
        return materiau.kappa_magnetique
    raise KeyError(f"Domaine inconnu : {domaine_nom!r}")
