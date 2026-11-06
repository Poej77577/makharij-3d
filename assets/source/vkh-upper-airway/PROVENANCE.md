# Published VKH upper-airway source snapshot

Repository: https://github.com/artisynth/artisynth_models
Commit: `e37be3f1b4831f347c055cbf7124b6bd57414f98`.

All 20 selected upstream files are unchanged and individually hashed in
`manifest.json`. The retained repository license expressly covers software
and data. Retain its notice, disclaimer, and required academic attribution.
This adds an independent research source; it does not obtain or substitute a
mirror of the denied MakeHuman system-assets ZIP.

`VKHUpperAirwayDemo.java` and its default body/FEM lists load these parts at
scale 1 in their common source frame. `tools/anatomy/mesh_sources.py` extracts
outward boundary triangles from the actual four-node tetrahedral elements.
The canonical mapping is `[(Y-110), (Z+180), (X+130)] * 0.001`, interpreting
native coordinates with the model's nominal millimeter convention. This is
an explicit authoring convention, not a measured person-specific scale.

The source assembly is inspected independently before fitting to the external
character. Maxilla and Mandible include bone and dental surfaces together;
they are not separately segmented crowns. Palatine aponeurosis is not labeled
as a complete velum/uvula or as vocal folds. The two suprahyoid FEM volumes
provide research muscle context, not an entire segmented oral mucosal floor.

The diagnostic source assembly and source-space renderings are in
`artifacts/milestone-evidence/M1/vkh-upper-airway`. Character placement is
recorded separately in `assets/calibration/character-fit.json` and must not
be described as clinical registration, a single donor, or expert approval.
