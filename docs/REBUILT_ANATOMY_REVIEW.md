# Rebuilt resting anatomy — review record

The user rejected the previous study's internal realism. The new model uses
actual Z-Anatomy / BodyParts3D anatomy in its common original frame, with a
continuous CC0 MakeHuman head and an authored source-based oral vestibule fit.
It does not use the rejected mixed-source tongue/nasal forms.

The editable result is `M2/realistic-rebuild/atlas-study.blend`. The actual GLB
has SHA-256 `1efc25de71de2f5489034274f185505cfb1539109c1f9f6a8f196e5bfb8cb2fc`.
`npm run assets:export` reproduces the source verification, tissue rebuild,
head/cavity fit, portable material bake and real-delivery checks.

## Changes relevant to visual review

- Rounded tongue with a shallow dorsal sulcus; true continuous root envelope
  derived from original tongue, genioglossus and hyoglossus volumes. Nested
  source muscle regions remain in the asset and have computed section faces.
- Source gingiva, individual teeth, palate, uvula, oral floor and pharyngeal
  structures share their original anatomical placement. New velar thickness
  has regularized tissue edges instead of a folded paper-thin shell.
- Source-shaped inferior nasal conchae have authored mucosal covers around
  actual nested bones. The negative nasal envelope removes unrelated head
  mass from the passage; it is not visible substitute anatomy.
- Source-guided oral/pharyngeal context cavities connect the anatomical spaces.
  The original connected visible lip rim is retained. Authoring parameters and
  changes are recorded; this is not a scan-registered patient or airflow model.
- The proximal trachea has actual inner/outer walls and annular open ports.
  Longitudinal source coordinates are preserved to prevent rim offset folds.
- Dorsal microstructure is a portable 2048px normal map. Section fibers and
  tissue appearance are illustrative, not measured microscopic anatomy.

## Evidence and limits

`anatomy-verification.json` verifies the actual GLB against the evaluated source,
required closed volumes, one tongue/root component, six authored surface
self-intersection checks and 29 selected rigid-tissue clearances. Contact
saturation fails the check. Oral/nasal section contours are validated and
triangulated independently; overlapping nested section regions are composed
without coincident cap triangles. This does not certify every possible source
organ interaction.

`atlas-captures.json` identifies actual Blender renders and source hashes.
`browser-verification.json` identifies the real production review page and
delivered file, one renderer, region controls, pointer rotation, eight actual
camera views and a mobile layout check. Software Chromium is not a physical
device performance measurement. No image-generation illustration substitutes
for the real model evidence.

This is a rebuilt **resting model for review**. Cranial/cervical tissues outside
the selected speech structures are simplified context. The fine source ethmoid
remains open uncapped skeletal context; complete vocal-fold anatomy and new
motion are not ready. Clinical anatomy and tajweed expert review remain pending.
The final acceptance gate deliberately remains failed until those reviews are
complete. Do not equate technical success with scientific or visual acceptance.

Adapted model data: CC BY-SA 4.0, with BodyParts3D and Z-Anatomy attribution.
CC0 head/eye notices and complete selected source notices are retained.
