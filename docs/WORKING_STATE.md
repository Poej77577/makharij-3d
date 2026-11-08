# Current implementation state — 2026-11-08

## Current nasal-cavity addition

The user explicitly requested an EMPTY connected nasal passage from nostrils to
beginning of throat. Implemented in `docs/NASAL_CAVITY.md`, source
`tools/blender/build_nasal_cavity.py`, specification `data/anatomy/nasal-cavity.json`.
Current nasal GLB db86baa8… contains positive hollow mucosal wall only; separate
analysis air GLB87152495… is not rendered as solid tissue. Source face now
`dce24684…` opens22 internal blind-cap quads and retains original vestibular rims,
UV/source IDs and4 face morphs. Both evaluated port rings match the new wall;
local4 nasal morphs follow them (10 checked face states). Oral013445a1 unchanged.
Actual open-path QA passes both inlets to the common nasopharyngeal outlet,
all3 ports, strict wall genus2 / air genus0 and positive-width path probes.
Runtime tab `الخيشوم` uses a parasagittal cut, optional guide and ghost context;
rest geometry only, not CFD or calibrated velopharyngeal closure. Dimensions
are inferred, clinical acceptance remains pending; no complete throat claim.
The older a91 nasal candidate passed route probes but had extra windows/genus4;
it is superseded and explicitly rejected by the strengthened topology gate.

## Latest user-directed improvement

The user requested continued autonomous work and a third team member. The
bounded team is the coordinator, method reviewer and independent contact
reviewer; do not expand it without a concrete need. Read `ORAL_SCULPT_REVIEW.md`
and `FACE_CONTEXT_REVIEW.md`. The old loft and both head reconstructions remain
rejected. Do not relabel technical progress as visual/anatomical acceptance.

Current home page: `/` (also `/mouth.html`), source `tools/blender/build_oral_sculpt.py`,
shape specification `data/anatomy/oral-sculpt.json`, editable native master and
GLB under `artifacts/method-evidence/oral-sculpt`. A separate original CC0
MakeHuman face is in `artifacts/method-evidence/face-context`; it does not use
the rejected atlas/Boolean composite. `/mouth.html` defaults to the face and
offers floor, whole-mouth and actual oral-section views. Runtime files use
`oral-study` and `face-context` names. Historical `makharij-realistic` files
are unchanged. This remains an experimental review tool.

Implemented: continuous six-patch tongue; nonplanar BVH-sampled closed mucosal
floor and frenulum; retained source anterior palatal mucosa with an attached
authored posterior soft palate/uvula; B-spline cage baked to
morphs; actual rigid jaw pivot and coupled lower dentition/gingiva; combined
jaw/tongue corrective shapes; constrained peak volume correction; portable PBR
maps using the pinned MIT skill; actual dynamic mesh-section caps in the browser;
three original facial lip targets, original bound eyes and one shared jaw state.
The combined native master has eight `SPEECH_CONTROLS` properties. Only the
dental jaw rotates rigidly; the skin receives its original face morph once.
Open head context is excluded from all tissue section caps.

Current revision: `ORAL_FORM_REVISION.md`. Blade/root contour and local gingival
fit were revised; duplicated anterior roof removed; posterior gingival ends
refined while preserving source faces/IDs and tooth-near vertices. A fresh velum
shape pins the anterior 15%. Added front/side/detail cameras, playback speed,
attributed actual PNG export and tuned real geometry shadows. `/legacy.html`
preserves the old technical inspector; `/anatomy.html` preserves the rejected atlas.

Older GLB `e22…` crossed dental surfaces in 17/36 selected pairs; `e051…` fixed
those but the expanded checker found lower-gingival crossings in 8/24 forbidden
tissue pairs. Current GLB `013445a15e55…` clears 36 dental pairs (18 poses,
min 4.264 mm) and 24 tongue/palate/gingiva pairs (8 poses, min 0.689 mm). Four actual
tongue rest/endpoint self-intersection checks are clear and unsaturated.
The old files and failures are retained. Staging requires matching full source,
dental, tissue and self reports; it does not approve anatomy. Face GLB
`dce24684…` has opened internal nasal caps and retains the oral identity; its 20 selected
face/dental surface pairs pass again. These checks do not prove all combinations,
tissue mechanics, adjacent-fold strain or phonetic fit.

Technical review covers 16 oral and 11 face native/GLB cases, including sampled
frenulum margins and 147 roof-interface points per oral case. Source/export
deviation is 0; peak tested tongue volume change is <2%, not a muscle simulation.
Nineteen unit checks and actual Chromium controls/caps/mobile/export review pass.
Visual review confirms clearer blade/root and improved roof/gums, but the broad
ventral horseshoe-like ridge remains after smoothing. Root/floor relationships,
posterior shape and full nasal/pharyngeal anatomy still need qualified sculpt
and human anatomy/tajweed review. Do not add letters or claim teaching/medical
acceptance from these tests. No scan or M2/M3 claim.

Use `assets:oral:*`, `assets:face:*` and `test:oral`. Build/check/contact-gate/stage
the oral unit before building the paired face. Old `assets:export` reconstructs a
rejected historical head; do not use it to publish this oral study. Material
rebaking starts from the retained untextured source. Any base-shape edit requires
rebuilding attachment, cage-derived shapes, export and evidence.

## Previous checkpoint

Latest binding direction: the user rejected this rebuild too and requested a different method.
The user explicitly authorized one specialist agent and internet skills. That
consultation is complete; do not restart a broad multi-agent search. Read
`TONGUE_PILOT_REVIEW.md`: an original bounded tongue pilot failed clay review
after one correction and must not become a third production anatomy model.
Its three actual GLB morph controls and rest return passed a ten-frame native
roundtrip comparison, which is mechanical evidence only. No anatomy milestone
has passed. The next source must be a qualified anatomical sculpt; it can be
static, with retopology/cage/rig authored afterwards. The MIT Blender skill is
installed in `.agents/skills/blender-image-to-3d` with local anatomy adaptations.
Read `ANIMATABLE_ASSET_ROUTE.md`. Stop using the atlas assembly as the production
visual foundation. Preserve both rejected studies. Work on source acquisition
and a deformation-first asset workflow; do not regenerate these meshes and
present another static study as the solution.

Historical direction before this rejection: rebuild the tongue and interior.
Follow `IMPLEMENTATION_PLAN.md` and `M2_VISUAL_REBUILD.md`. Work alone, solve
routine implementation issues autonomously, and do not rig rejected anatomy.

## Rejected historical reconstruction

The rejected study is `artifacts/milestone-evidence/M2/realistic-rebuild`, alongside the earlier rejected
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

## New route evidence

The new route is documented in `ANIMATABLE_ASSET_ROUTE.md` and the concrete
asset specification in `ANATOMICAL_ASSET_BRIEF.en.md`. A native Ematoblender
release file was audited without running its scripts. Jaw and side-lip probes
changed face vertices and returned to rest; its tongue had no bound rig and
remained unchanged. One constrained upper-lip rotation produced no movement.
These are mechanical observations, not visual/anatomical approval. Its asset
rights remain unresolved; source geometry is outside the repository and is not
redistributed. MRI-derived companion datasets have NC-ND restrictions.

The review found no complete source ready for adoption among the inspected
assets. Professional marketplace inspection is still blocked by CONNECT 403.
A five-domain draft was saved but not applied; current custom domains remain
empty. Do not treat the user's generic “continue” as network or spending approval.
Refresh runtime status after a real settings change and retry with a fresh
connection. Generic autonomy does not itself apply a network-policy draft.
The later explicit third-agent request supersedes the older one-specialist
budget, with three total team members retained. Do not return to atlas
remeshing or the failed section-loft pilot.

## Recovery

Branch `codex/anatomy-foundation-v2`, origin `Poej77577/makharij-3d`.
Pushed checkpoint `2702599` preserves the rejected study and its diagnostics.
Earlier Ra study remains in Git; recovery bundle is under
`/workspace/artifacts/recovery-2026-11-06`. Preserve history, no main merge or
public deployment. Package current sources with `package:source`.

Environment works; Blender 4.3.2 CPU, native Python QA and Node are separate.
Keep proxy/TLS unchanged, do not bypass denied hosts. Optional MakeHuman ZIP
restrictions no longer block this anatomy source route.
