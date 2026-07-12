class CalculAnnule(Exception):
    pass


def verifier(annule) -> None:
    if annule is not None and annule():
        raise CalculAnnule("Calcul annulé par l'utilisateur.")
