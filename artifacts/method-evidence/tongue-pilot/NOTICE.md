# Rejected tongue authoring pilot

This is a failed visual study and a technical morph/export fixture. It is not
MAKHARIJ's selected anatomy, a clinically measured tongue, or an Arabic speech
pose library. Read `visual-review.json` and `docs/TONGUE_PILOT_REVIEW.md`.

The tongue and open guide surfaces were authored for this experiment from
explicit, inferred section dimensions. No MB-Lab, Ematoblender or MRI dataset
geometry is included. The user's reference illustration is not redistributed.

The native review scenes and contextual PNGs include existing reference
dentition/gingiva from the project's licensed Z-Anatomy snapshot. They retain:

- BodyParts3D — Kousaku Okubo / The Database Center for Life Science — CC BY-SA
  2.1 Japan: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
- Z-Anatomy — Gauthier Kervyn / The libre 3D atlas of anatomy — CC BY-SA 4.0:
  https://github.com/Z-Anatomy/Models-of-human-anatomy

Model scenes/adaptations follow the project's CC BY-SA 4.0 model-data terms.
Required publisher notices and extraction provenance remain under
`assets/source/z-anatomy/NOTICE.md` and `LICENSE.publisher.txt`. Changes here:
coordinate rotation for Blender review, neutral materials and disposable real
sagittal cuts; the atlas tongue/head/velum are not used. The pilot GLB contains
only the new tongue, not the atlas context or guide surfaces. This model-data
notice does not relicense independent application code.

The review-render helper is MIT, Majid Manzarpour; its exact license, upstream
commit/hashes and local safety/anatomy adaptations are preserved in
`.agents/skills/blender-image-to-3d`.
