# Current implementation state — 2026-11-07

Latest binding direction: rebuild the unrealistic tongue and interior.
Follow `IMPLEMENTATION_PLAN.md` and `M2_VISUAL_REBUILD.md`. Work alone, solve
routine implementation issues autonomously, and do not rig rejected anatomy.

## Active reconstruction

Use `artifacts/milestone-evidence/M2/realistic-rebuild`, not the rejected
mixed-source `character-assembly`. The new internal foundation is actual
selected Z-Anatomy / BodyParts3D geometry in its original common frame.
The external CC0 MakeHuman head receives one dental atlas translation.
This is a source-guided authoring fit, not clinical registration of one donor.

- Source commit `8dd357ed52a675db0c5f8d7fa9a8621cbfeee713`, 75 selected
  evaluated meshes. Source units, frame, original archive and startup hashes
  are retained. Immutable extracted snapshot: `assets/source/z-anatomy`.
- Rounded tongue and shallow dorsal sulcus; actual genioglossus/hyoglossus
  source regions form one continuous tongue/root envelope. Original internal
  muscle regions remain for genuine volume-section inspection.
- Actual gingiva, dentition, palatal/uvular, floor muscle, nasal, pharyngeal,
  epiglottic and laryngeal cartilage structures retained. Authored velar
  thickness, hollow proximal tracheal context and topology repairs recorded.
  Two source-shaped inferior turbinate mucosal envelopes cover the original
  nested concha bones. Positive tissue covers remain distinct from airspaces.
- Source ethmoid remains open uncapped skeletal context: no invented closed
  tissue claim. Nose, mandible and tongue have controlled surface reduction.
- Actual source-guided negative cavities are independently preflighted.
  Robust Manifold3D head Boolean preserves original UV/material provenance.
  A recorded submillimeter negative-envelope margin resolves coincident
  source-wall films; actual positive organs retain their common source frame.
- The original connected lip rim is unchanged. The unrelated deep MakeHuman
  oral bag is compressed to a front vestibule and replaced by source-guided
  oral context around the actual tongue, gingiva and velum. No primitive
  substitute organs. This authored context is not measured patient airflow.
- Tongue dorsal microstructure is baked into a portable 2048px normal map.
  Material fibers and microstructure are illustrative, not scanned histology.
- `/anatomy.html`: actual static model, one renderer, external/computed sagittal
  view, rotation/zoom and regional focus. Legacy inspector remains on `/`.
  Static view renders on demand, with damping frames while the camera moves.
  Oral and nasal sections use 5.01 mm and 9.01 mm parasagittal planes of the
  same real asset. Nested muscle surfaces render through their true sections
  inside the continuous tongue envelope.

Latest static delivery: 79 source/derived structures, 407,016 triangles,
9,581,628-byte GLB, tongue/root one component (~38.98 mL). Six authored tissue
surfaces have no detected nonadjacent FCL self intersections, with unsaturated
checks. 29 selected tongue/teeth/mandible pairs are clear (smallest distance
~0.333 mm). These are selected static diagnostics, not clinical validation.

## Reproduction and evidence

`npm run assets:export` runs the new pipeline and stages matching GLB,
sections, manifest and attribution under `public/models`. Native stage input
`internal-rest.blend` is separate from composed `atlas-study.blend`; fitting
always reloads the native stage and never translates an already fitted file.

`assets:validate` and `test:geometry` inspect the real delivered GLB: identity,
closed required tissue volumes, root connectivity, sections and selected
static tongue/teeth/mandible clearances. They do not claim every collision or
expert approval. `assets:acceptance` must still fail until real visual and
expert acceptance. Do not infer quality from part/triangle counts.

`evidence:capture` renders actual geometry using Cycles CPU and tests the
production review page in Chromium. Read current measurements and scope in
`anatomy-verification.json`, `atlas-airspace-verification.json`,
`atlas-sections.json` and `browser-verification.json`.

Pending: critical visual/expert anatomy and tajweed review, calibrated
landmarks, then M3 rig and the first five letters ر ق م ف ع. No new-letter
readiness claim. The new resting model does not inherit the old Ra morphs.

## Recovery

Branch `codex/anatomy-foundation-v2`, origin `Poej77577/makharij-3d`.
Pushed checkpoint `2702599` preserves the rejected study and its diagnostics.
Earlier Ra study remains in Git; recovery bundle is under
`/workspace/artifacts/recovery-2026-11-06`. Preserve history, no main merge or
public deployment. Package current sources with `package:source`.

Environment works; Blender 4.3.2 CPU, native Python QA and Node are separate.
Keep proxy/TLS unchanged, do not bypass denied hosts. Optional MakeHuman ZIP
restrictions no longer block this anatomy source route.
