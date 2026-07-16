# Guide du professeur — FieldLab 2

Ce guide propose des séances courtes avec le mode **Cours**. Dans tous les cas : lancez d’abord le preset sans le modifier, faites formuler une prédiction aux élèves, puis changez un seul paramètre. Les sondes servent aux mesures ponctuelles ; le profil 1D permet une comparaison quantitative ; l’export 4K fournit la figure de synthèse.

## Page 1 — Électrostatique

### Condensateur plan : relier potentiel et champ

Objectif : visualiser des équipotentielles presque parallèles et vérifier `E ≈ ΔV/d` loin des bords. Lancez le scénario, tracez un profil perpendiculaire aux plaques et relevez deux potentiels avec les sondes. Doublez la tension : le profil de potentiel et `|E|` doivent doubler, mais garder la même forme. Les écarts près des extrémités illustrent les effets de bord.

### Cage de Faraday : blindage électrostatique

Objectif : distinguer conducteur, cavité et espace extérieur. Affichez l’intensité du champ, placez une sonde dans la cavité puis à l’extérieur et discutez le rôle du potentiel imposé sur l’enceinte. La simulation 2D représente une enceinte extrudée, pas une cage sphérique isolée.

### Condensateur avec diélectrique partiel : rôle de la matière

Objectif : comparer air et verre. Superposez lignes de champ et carte scalaire, puis faites passer un profil à travers le diélectrique. La permittivité relative modifie localement le champ et la pente du potentiel. Passez en mode Expert seulement pour montrer le coefficient `εr` ou raffiner le maillage.

Activité de synthèse : exporter une image 4K du condensateur, avec deux sondes et un titre indiquant la tension et la distance entre plaques.

## Page 2 — Magnétostatique

### Fil infini : loi en `1/r`

Objectif : vérifier `B(r)=μ₀I/(2πr)`. Affichez `|B|`, tracez un profil radial qui ne traverse pas le cœur du fil et comparez deux distances. En doublant `r`, le champ doit être approximativement divisé par deux ; en doublant le courant, il double. Le modèle 2D suppose un fil invariant suivant l’axe hors plan et utilise `J` en A/m².

### Deux fils parallèles : superposition

Objectif : prévoir où les champs s’ajoutent ou se compensent. Comparez « même sens » et « opposés » en gardant le courant identique. Demandez aux élèves de tracer le sens du champ avant d’afficher les lignes. Utilisez une sonde sur l’axe médian pour rendre la compensation mesurable.

### Bobines de Helmholtz 3D : zone uniforme

Objectif : montrer la construction d’un champ presque uniforme par deux bobines espacées de leur rayon. Utilisez la coupe centrale et la sonde-ligne 3D. Le calcul emploie Biot–Savart **dans le vide** : un noyau de fer ne peut pas être étudié dans ce mode et les matériaux magnétiques sont volontairement désactivés.

Activité de synthèse : exporter le profil central en CSV et faire calculer l’écart relatif du champ autour du centre.

## Page 3 — Thermique

### Mur composite : flux et rupture de pente

Objectif : relier gradient thermique et conductivité. Tracez un profil normal au mur : la température reste continue, mais sa pente change à l’interface verre/plastique. Identifiez la couche qui porte la plus grande chute de température et reliez-la à sa résistance thermique.

### Trempe dans l’eau : échelle de diffusion

Objectif : lire un temps physique. Le preset choisit de l’eau réelle et une durée de l’ordre de la diffusion. Lancez l’animation en ×1000 : le facteur accélère uniquement la lecture, pas la physique. Épinglez une sonde au centre du cuivre et une dans l’eau, puis exportez le MP4 avec horodatage. Rappelez que FieldLab ne modélise que la conduction ; la convection naturelle accélérerait le refroidissement réel.

### Ailette de refroidissement ou plancher chauffant

Objectif : étudier l’influence de la géométrie. Pour l’ailette, observez comment l’aluminium étale le flux depuis la base chaude. Pour le plancher, suivez la diffusion vers le haut et discutez les conditions aux limites. Modifiez la taille avant la température : l’échelle de temps varie approximativement comme `L²`.

Activité de synthèse : produire une image 4K annotée, un profil `T(x)` et une animation dont le temps simulé est lisible en minutes ou en heures.

## Conseils communs

- Mode Cours : valeurs sûres et quatre clics maximum jusqu’à l’image exportée.
- Mode Expert : étude du maillage, des conditions Dirichlet/Neumann/Robin, de la tolérance et de la convergence.
- Une image « jolie » ne prouve pas la convergence : augmentez la résolution et vérifiez que les valeurs de sonde changent peu.
- Pour comparer deux réglages, utilisez **Analyse → Mémoriser la référence A**, puis **Comparer B à A**.
