import math


def flux_absorbe(flux_solaire: float, angle_incidence_deg: float, alpha: float) -> float:
    angle = max(0.0, min(90.0, angle_incidence_deg))
    return max(0.0, alpha * flux_solaire * math.cos(math.radians(angle)))


def coefficient_reflexion(alpha: float) -> float:
    return 1.0 - max(0.0, min(1.0, alpha))
