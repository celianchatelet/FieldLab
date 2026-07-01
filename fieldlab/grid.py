from dataclasses import dataclass, field
import numpy as np


@dataclass(eq=False)
class Field:
    V: np.ndarray
    fixed_mask: np.ndarray
    solid_mask: np.ndarray = None
    h: float = 1.0
    walls: dict = None
    omega: float = None
    source: np.ndarray = None

    free: np.ndarray = field(init=False, repr=False)
    rouge: np.ndarray = field(init=False, repr=False)
    noir: np.ndarray = field(init=False, repr=False)
    fluid: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        if self.solid_mask is None:
            self.solid_mask = np.zeros(self.V.shape, dtype=bool)
        if self.source is None:
            self.source = np.zeros(self.V.shape)
        if self.walls is None:
            self.walls = {c: ("neumann",) for c in ("haut", "bas", "gauche", "droite")}
        if self.V.shape != self.fixed_mask.shape:
            raise ValueError("V et fixed_mask doivent avoir la meme forme.")

        self.fluid = ~self.solid_mask

        i, j = np.indices(self.V.shape)
        couleur = (i + j) % 2
        interieur = np.zeros(self.V.shape, dtype=bool)
        interieur[1:-1, 1:-1] = True
        self.free = interieur & ~self.fixed_mask & ~self.solid_mask
        self.rouge = self.free & (couleur == 0)
        self.noir = self.free & (couleur == 1)

    @property
    def shape(self):
        return self.V.shape

    @property
    def N(self):
        return max(self.V.shape)

    def copy(self):
        return Field(self.V.copy(), self.fixed_mask.copy(),
                     self.solid_mask.copy(), self.h, dict(self.walls),
                     self.omega, self.source.copy())
