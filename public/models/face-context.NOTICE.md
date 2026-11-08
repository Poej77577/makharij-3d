# External face context — experimental

The original MakeHuman head/body topology, adult macro targets, facial targets
and bound eye mesh/texture are CC0 assets from:
https://github.com/makehumancommunity/makehuman
commit `a8bc2d54ff0ac92e78ff71431b1023eda42bf482`.
The original notices and per-file hashes are retained under
`assets/source/makehuman`. Asset and software licenses are separate; upstream
application code was not incorporated to construct this face.

Project changes: select the external head/neck body surface; crop and flatten
the neck boundary; retain original UV and coarse source-vertex identifiers;
author a smooth vermilion pigment field; evaluate original facial targets
through one subdivision and bake their identical topology to morph targets;
translate using the upper-incisor helper anchor. The source generic oral
pocket is retained as a hidden, unmodified reference and is not delivered as
speech anatomy. No rejected atlas composite, cavity Boolean or compressed
oral bag is used.

The delivered GLB contains only the external face surface and eyes. It is an
external context, not closed cranial tissue, a scan or a complete internal
head. It must be excluded from tissue section caps. Jaw-skin, lip/dental fit
and Arabic phonetic calibration remain subject to review. Original face
shape targets move the skin; do not add a second rigid jaw rotation to it.

The editable native scene also contains the separately attributed oral-unit
reference, which includes CC BY-SA 4.0 Z-Anatomy / BodyParts3D dental data.
See `../oral-sculpt/NOTICE.md` and `assets/source/z-anatomy/NOTICE.md`.
Combined model adaptations use the project's CC BY-SA 4.0 model-data terms;
original CC0 rights remain available and independent application code is not
relicensed by this notice.

The two original blind internal nasal caps (22 source quads) are now removed
to connect the retained external nostril/vestibular rims to the separate nasal
cavity study. Original source IDs, UVs and all four face targets are retained.
This does not certify the inferred internal nasal anatomy.
