from dataclasses import dataclass

import numpy as np
import skfem

from fieldlab.fem3d.mesh import FACES


@dataclass(eq=False)
class Field3D:
    mesh: skfem.MeshTet
    basis: skfem.Basis
    V: np.ndarray
    fixed_mask: np.ndarray
    solid_mask: np.ndarray = None
    walls: dict = None
    source: np.ndarray = None
    kappa: np.ndarray = None






    vecteurs: np.ndarray = None



    libelle_scalaire: str = None



    scene: object = None



    rho_cp: np.ndarray = None

    # Conversion de la densité physique vers le second membre de Poisson.
    facteur_source: float = 1.0

    def __post_init__(self):
        n = self.basis.N
        if self.solid_mask is None:
            self.solid_mask = np.zeros(n, dtype=bool)
        if self.source is None:
            self.source = np.zeros(n)
        if self.kappa is None:
            self.kappa = np.ones(n)
        if self.rho_cp is None:
            self.rho_cp = np.ones(n)
        if self.walls is None:
            self.walls = {f: ("neumann",) for f in FACES}
        self.facteur_source = float(self.facteur_source)
        for nom, tableau in (("V", self.V), ("fixed_mask", self.fixed_mask),
                              ("solid_mask", self.solid_mask),
                              ("source", self.source), ("kappa", self.kappa)):
            if tableau.shape != (n,):
                raise ValueError(
                    f"{nom} doit avoir la forme ({n},), recu {tableau.shape}.")
        if self.vecteurs is not None and self.vecteurs.shape != (n, 3):
            raise ValueError(
                f"vecteurs doit avoir la forme ({n}, 3), recu {self.vecteurs.shape}.")

    @property
    def N(self) -> int:
        return self.basis.N

    def copy(self) -> "Field3D":
        return Field3D(
            mesh=self.mesh,
            basis=self.basis,
            V=self.V.copy(),
            fixed_mask=self.fixed_mask.copy(),
            solid_mask=self.solid_mask.copy(),
            walls=dict(self.walls),
            source=self.source.copy(),
            kappa=self.kappa.copy(),
            vecteurs=(None if self.vecteurs is None
                      else self.vecteurs.copy()),
            libelle_scalaire=self.libelle_scalaire,
            scene=self.scene,
            rho_cp=self.rho_cp.copy(),
            facteur_source=self.facteur_source,
        )
