# Selected Z-Anatomy head and neck geometry

Model content is licensed under **CC BY-SA 4.0**. Retain the original publisher
notice in `LICENSE.publisher.txt` and the following required attributions:

- **BodyParts3D - The Database Center for Life Science - CC-BY-SA 2.1 Japan**.
  https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
- **Z-Anatomy - The libre 3D atlas of anatomy - CC-BY-SA 4.0**.
  https://github.com/Z-Anatomy/Models-of-human-anatomy
  https://creativecommons.org/licenses/by-sa/4.0/

Original BodyParts3D model: Kousaku Okubo. Atlas design, anatomy and 3D work:
Gauthier Kervyn. The complete publisher credits remain in the retained notice.

This is a selected **derived geometry snapshot**, not the entire upstream ZIP.
The original archive and startup Blender file are identified by hashes in
`manifest.json`. Source object names and evaluated modifiers are recorded in
`extraction.json`; original source units are stored in `source-units.json`.

Changes at extraction: evaluated the source's existing modifiers, converted
the common world frame to meters/+X anterior/+Y superior/+Z right using the
recorded rigid transform, removed unrelated objects/application code/definitions,
and assigned new study materials. Surface shapes are otherwise preserved.
`construction-surfaces.json` retains the source mucosal/velar surfaces before
the original Solidify modifier for documented tissue reconstruction.

Selected structures are core oral, nasal, skeletal and throat anatomy. The
separately attributed third-party inner-ear, kidney and brain/white-matter
content is not selected or redistributed. Wikipedia definitions and the
application-template scripts are not copied into the product.

Redistributed adaptations of these model surfaces must retain attribution,
indicate modifications, and use CC BY-SA 4.0. This model-data license does not
relicense independent application code. Geometry inspection and source
licensing do not establish clinical accuracy or expert approval.
