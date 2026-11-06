# MAKHARIJ — ENGINEERING IMPLEMENTATION PLAN

## Mission

Build an anatomically coherent, realistic, animated Arabic articulation platform.

The first production milestone is:
- A convincing external human head.
- Compatible volumetric internal anatomy.
- Independent articulation controls.
- Five technically demonstrated sounds: ر، ق، م، ف، ع.
- A working browser viewer.

Then expand into the complete student and teacher platform.

Communicate with the user in Arabic.
The product interface and educational content must be Arabic and RTL.

Use one primary agent by default. Add at most one specialist for a clearly justified independent task.

Do not treat this document as a request to create scaffolding only. Implement working vertical slices with evidence.

---

## 1. Architecture decisions

Use a simple single-application repository:

- Frontend: React + TypeScript + Vite.
- Rendering: Three.js.
- Asset authoring: Blender.
- Browser asset format: glTF/GLB.
- Runtime schema validation: Zod or an equivalent typed validator.
- Unit and integration tests: Vitest.
- Browser tests: Playwright.
- Offline geometry QA: a separate Python environment.
- No backend until a concrete feature requires one.

Use one WebGL renderer with multiple viewports.

Use one playback clock for the articulation state.
The external and sagittal views must show the same pose and time.

Author anatomy and deformation in the asset pipeline.
The browser should play calibrated animations and render the model.
Do not generate substitute speech organs from primitive geometry at runtime.

Pin tool versions after inspecting the available environment.
Keep Blender’s Python environment separate from native Python QA dependencies.

---

## 2. Repository structure

Use this structure unless an existing repository convention provides a better equivalent:

/
├── assets/
│   ├── source/
│   │   ├── anatomy-master.blend
│   │   └── original-assets/
│   ├── calibration/
│   │   ├── landmarks.json
│   │   ├── regions.json
│   │   └── controls.json
│   └── licenses/
│       ├── registry.json
│       └── notices/
├── public/
│   └── models/
│       ├── makharij.glb
│       └── anatomy.manifest.json
├── src/
│   ├── domain/
│   │   ├── anatomy.ts
│   │   ├── articulation.ts
│   │   └── schemas.ts
│   ├── motion/
│   │   ├── PlaybackClock.ts
│   │   └── ArticulationEngine.ts
│   ├── viewer/
│   │   ├── AnatomyViewer.ts
│   │   ├── AssetLoader.ts
│   │   ├── CameraController.ts
│   │   ├── SectionRenderer.ts
│   │   └── LabelLayer.ts
│   ├── content/
│   │   ├── letters/
│   │   └── sources/
│   └── ui/
│       ├── StudentView.tsx
│       ├── TeacherView.tsx
│       └── controls/
├── tools/
│   ├── blender/
│   │   ├── inspect_asset.py
│   │   ├── validate_source.py
│   │   ├── export_model.py
│   │   └── render_evidence.py
│   └── qa/
│       ├── evaluate_export.py
│       ├── check_geometry.py
│       └── capture_browser.py
├── tests/
│   ├── unit/
│   └── e2e/
├── docs/
│   ├── ASSET_DECISION.md
│   ├── ANATOMY_SPEC.md
│   ├── RIG_CONTRACT.md
│   ├── VALIDATION.md
│   └── WORKING_STATE.md
└── artifacts/
    └── milestone-evidence/

Keep source assets, generated browser assets, calibration data, and evidence clearly separated.

Never overwrite the editable master file merely to produce a render or diagnostic export.

---

## 3. Canonical asset contract

Use a documented right-handed browser coordinate frame:

- Units: meters.
- +X: anterior.
- +Y: superior.
- +Z: subject’s right.

Document and test the conversion from Blender/source coordinates.
Do not compensate for incorrect axes with undocumented camera or runtime rotations.

Give anatomical structures stable semantic identifiers.

Do not assume:
- One anatomical structure equals one mesh.
- One mesh has only one material.
- Vertex indices remain stable after retopology or optimization.

A continuous facial mesh may contain upper-lip and lower-lip regions.
Do not split the face into disconnected objects merely to satisfy a naming convention.

Suggested TypeScript contracts:

type ReviewState = "pending" | "pass" | "fail";

interface StructureBinding {
  id: string;
  nodeIds: string[];
  regionId?: string;
  sourceKind: "acquired" | "authored" | "mixed";
  licenseIds: string[];
}

interface AnatomyManifest {
  schemaVersion: number;
  assetVersion: string;
  glbSha256: string;
  units: "m";
  coordinateFrame: {
    anterior: "+X";
    superior: "+Y";
    right: "+Z";
  };
  structures: StructureBinding[];
  clips: {
    name: string;
    durationSeconds: number;
  }[];
  review: {
    geometry: ReviewState;
    visual: ReviewState;
    anatomyExpert: ReviewState;
    tajwidExpert: ReviewState;
  };
}

type ArticulationPhase =
  | "rest"
  | "prepare"
  | "approach"
  | "articulate"
  | "hold"
  | "release"
  | "return";

type AirflowState =
  | "oral"
  | "nasal"
  | "both"
  | "occluded"
  | "not_visualized";

interface PhaseInterval {
  phase: ArticulationPhase;
  startSeconds: number;
  endSeconds: number;
  airflow: AirflowState;
}

interface ContactRequirement {
  kind: "contact" | "narrowing" | "closure";
  activeRegionId: string;
  targetRegionId: string;
  startSeconds: number;
  endSeconds: number;
  calibrationRef: string;
}

interface ArticulationDefinition {
  id: string;
  arabicLabel: string;
  groupId: string;
  clipName: string;
  calibrationAssetSha256: string;
  phases: PhaseInterval[];
  contacts: ContactRequirement[];
  sourceRefs: string[];
  availability: "ready" | "experimental" | "not_implemented";
}

Validate these contracts at runtime.

Reject:
- Missing required structures.
- Unknown animation clips.
- Invalid phase intervals.
- Calibration bound to a different asset.
- Missing or unresolved redistribution rights.

Never replace a failed asset with procedural placeholder anatomy.

---

## 4. Runtime data flow

Use this flow:

User input
→ PlaybackClock / ArticulationEngine
→ PlaybackSnapshot
→ Three.js animation evaluation
→ Both camera views
→ Labels and educational overlays

The playback snapshot should contain only the canonical playback state, for example:

interface PlaybackSnapshot {
  letterId: string;
  clipName: string;
  clipTimeSeconds: number;
  phase: ArticulationPhase;
  airflow: AirflowState;
  playing: boolean;
  speed: number;
}

The engine owns playback timing and state transitions.
The viewer owns rendering and applying the selected animation.

Do not create independent timelines for different viewports.
Do not rebuild or reload the model when switching letters.

Use source-authored, calibrated glTF animation clips as the initial playback mechanism.

Keep experimental manual rig controls in a diagnostic tool until their combinations are verified.

---

# IMPLEMENTATION MILESTONES

## M0 — Bootstrap and recoverability

Tasks:

M0.1 Inspect the repository and preserve existing changes.
M0.2 Verify the development environment.
M0.3 Create the minimal application and tool entry points.
M0.4 Establish a development branch and recovery procedure.
M0.5 Verify an external backup of completed work.

Deliver:
- A working build.
- Startup instructions.
- Version records.
- A verified recovery checkpoint.

Acceptance:
- The application can start from documented commands.
- The backup can be identified and recovered.
- No existing work has been silently discarded.

Do not spend this milestone designing the final interface.

---

## M1 — Inspect and select the anatomical foundation

Tasks:

M1.1 Inspect a small number of serious anatomical candidates.
M1.2 Read licenses and redistribution conditions.
M1.3 Inspect actual geometry, not publisher previews.
M1.4 Evaluate external face quality and internal coverage.
M1.5 Record missing structures and fitting requirements.
M1.6 Select a foundation or a professional reconstruction approach.

Write:
- docs/ASSET_DECISION.md
- assets/licenses/registry.json
- Initial docs/ANATOMY_SPEC.md

Acceptance:
- Actual files were opened and inspected.
- Rights are documented.
- The selected approach can support both external realism and internal articulation.

Do not automatically select an asset because it is academic, medical, or advertised as rigged.

Reject scan supports and dental-cast bases as anatomical substitutes.

---

## M2 — Build the realistic resting anatomy

This is an asset-production milestone, not a UI milestone.

Tasks:

M2.1 Establish compatible head and internal-organ proportions.
M2.2 Sculpt or refine the external head.
M2.3 Build continuous perioral tissue and volumetric lips.
M2.4 Fit teeth, gingiva, palates, tongue, and mouth floor.
M2.5 Establish genuine oral, nasal, and pharyngeal cavities.
M2.6 Complete necessary throat/laryngeal coverage.
M2.7 Retopologize for deformation.
M2.8 Prepare UVs, normals, and initial materials.

External quality requirements:
- Natural front, side, and three-quarter silhouettes.
- Coherent nose, lips, chin, jaw, and neck.
- Appropriate lip thickness and natural mouth corners.
- Teeth seated inside the mouth.
- No floating patches or ribbon-like tissue.

Internal quality requirements:
- A full tongue connected to its root and mouth floor.
- Distinguishable tongue regions.
- Compatible hard and soft palates.
- Clear uvula.
- Genuine cavities and tissue boundaries.
- No masses filling the teaching spaces.

Professional sculpting and retopology are permitted.
Procedural tools may support production, but primitive assemblies must not serve as the final anatomical model.

Evidence:
- Front, side, and three-quarter renders.
- Mouth close-up.
- Sagittal cutaway.
- Full-volume rotation.
- Close-ups of tongue/floor, lips, teeth, and palate.

Acceptance:
- The model is convincing before animation.
- External and internal anatomy agree spatially.
- Major structural defects are resolved.

Do not mark this milestone complete based on mesh counts, loading success, or automated topology checks alone.

Record visual and expert-review status honestly.

---

## M3 — Build the rig and export pipeline

Tasks:

M3.1 Build the lower-jaw pivot and coupling.
M3.2 Bind lower teeth and gingiva to the jaw.
M3.3 Create tongue-tip, blade, dorsum, root, lateral, and groove controls.
M3.4 Create lip closure, opening, rounding, protrusion, and lower-lip contact controls.
M3.5 Create soft-palate and uvular controls.
M3.6 Add appropriate surrounding facial deformation.
M3.7 Define stable rig names and calibration references.
M3.8 Implement reproducible export and manifest generation.

Use a hybrid rig:
- Rigid transforms where anatomically appropriate.
- Bones, shape keys, or corrective deformation for soft tissues.
- Offline corrective authoring for contact and tissue preservation.

Avoid implementing a general-purpose muscle simulator in the browser.

Write:
- docs/RIG_CONTRACT.md
- assets/calibration/controls.json
- assets/calibration/landmarks.json
- assets/calibration/regions.json

Acceptance:
- Each required control works independently.
- Useful control combinations preserve believable anatomy.
- Exported controls and clips match the manifest.
- Facial tissue moves coherently with the lips and jaw.
- Tongue motion is nonrigid.

Region bindings must be tied to the asset version.
Rebuild or verify them after retopology or mesh optimization.

---

## M4 — Implement and verify five core articulations

Implement separate clips for:

- Ra — ر
- Qaf — ق
- Mim — م
- Fa — ف
- ‘Ayn — ع

Required behavior:

Ra:
Appropriate tongue-tip articulation, controlled contact/release, and a documented tafkhim/tarqiq context.

Qaf:
Posterior tongue closure and release near the appropriate soft-palate region.

Mim:
Bilabial closure coordinated with a nasal route through appropriate velum movement.

Fa:
Inner lower-lip interaction with upper incisor edges.

‘Ayn:
Appropriate pharyngeal articulation with documented anatomical and phonetic limits.

Tasks:

M4.1 Author distinct clips and phase markers.
M4.2 Bind intended contact/narrowing regions.
M4.3 Check approach, maintenance, release, and return.
M4.4 Check external facial behavior.
M4.5 Export the clips.
M4.6 Independently evaluate the delivered asset.
M4.7 Capture actual front and sagittal videos.

Acceptance:
- The five articulations are visibly and mechanically distinct where appropriate.
- No significant unintended tooth/palate penetration.
- No lip self-intersection or major tissue collapse.
- Closure is examined across its relevant extent.
- Intermediate states are evaluated.
- Playback returns to the intended resting state.
- Limitations and pending expert review are documented.

Do not treat lip closure alone as a completed Mim.
Do not treat a central nearest-point contact as proof of a full Qaf closure.

After repeated failures, diagnose geometry, fitting, or control design before continuing parameter tuning.

---

## M5 — Implement the production viewer

Tasks:

M5.1 Implement AssetLoader with manifest validation.
M5.2 Implement the single-renderer multi-viewport viewer.
M5.3 Add external, sagittal, and full-volume modes.
M5.4 Implement PlaybackClock and ArticulationEngine.
M5.5 Add play, pause, reset, seek, and speed controls.
M5.6 Add camera orbit, zoom, pan, focus, and reset.
M5.7 Add anatomical labels and region highlighting.
M5.8 Add visibility controls.
M5.9 Implement computed section surfaces where valid.
M5.10 Add responsive Arabic UI.

Section-rendering requirements:
- Follow actual deformed geometry.
- Cap only valid tissue volumes.
- Preserve genuine cavities.
- Hide section surfaces with their associated structures.
- Prevent clipping/stencil state from leaking between views.

Acceptance:
- Both views display the same articulation state.
- Seeking and playback produce consistent poses.
- Reset is repeatable.
- Camera controls do not alter articulation state.
- Missing assets produce a clear error.
- Repeated mounting, switching, and unloading do not leak renderer resources.
- No decorative or nonfunctional controls.

---

## M6 — Add educational and teacher features

Tasks:

M6.1 Organize letters by the five major makharij groups.
M6.2 Add concise Arabic explanations and common mistakes.
M6.3 Add teacher presentation mode.
M6.4 Add meaningful letter comparison.
M6.5 Save lesson/display settings locally.
M6.6 Expand articulation coverage in reviewed groups.
M6.7 Add verified Quranic examples.
M6.8 Add licensed audio when available.

Content requirements:
- Distinguish makhraj from sifah.
- Distinguish contact from narrowing.
- Distinguish madd from non-madd counterparts.
- Represent nasal routing consistently.
- Respect Lam, Dad, lateral articulation, and grooving.
- Do not invent visual differences merely for variety.
- Distinguish traditional tajwid concepts from modern phonetic terminology.

Audio:
- Record source and redistribution rights.
- Do not present TTS as approved recitation.
- Mark unavailable audio as pending.
- Claim synchronization only after testing it.

Avoid authentication, administration, and backend services until a concrete requirement justifies them.

---

## M7 — Optimize and release

Tasks:

M7.1 Profile the actual model and rendering.
M7.2 Establish documented loading, memory, and rendering budgets.
M7.3 Optimize meshes and textures while preserving articulation.
M7.4 Recheck the optimized delivered asset.
M7.5 Test the production build.
M7.6 Package editable assets, code, licenses, and evidence.
M7.7 Verify external backup and any deployment.

Do not introduce lower-detail variants that invalidate contact regions or articulation without checking those variants.

Acceptance:
- Final browser assets match their manifest and calibration.
- Production functionality passes.
- Device/performance claims match actual measurements.
- A phone viewport simulation is not reported as a physical phone test.
- Remaining issues are documented.
- Source files and recovery instructions are delivered.
- Deployment is claimed only with a verified working URL.

---

## 5. Verification strategy

Maintain three separate verification layers:

A. Source asset verification
- Anatomy inventory.
- Units and coordinate conversion.
- Topology and normals.
- Appropriate tissue thickness.
- Intended openings and attachments.
- Rig and control behavior.

B. Exported asset verification
- Decode/evaluate the actual delivered GLB.
- Include node transforms, skinning, morph targets, and supported compression.
- Do not test only the undeformed base mesh.
- Verify semantic bindings and animation clips.
- Evaluate intermediate articulation states.

C. Browser verification
- Actual loading and deformation.
- Timeline behavior.
- View synchronization.
- Section and visibility behavior.
- Camera interactions.
- Errors, resources, and production behavior.

Separate:
- Geometry test results.
- Visual review.
- Anatomical expert review.
- Tajwid expert review.

Do not claim expert approval from automated tests.

Use geometric checks appropriate to the structure.
Do not assume an intentionally open context surface is a closed volume.

Document tolerances and the limits of sampled tests.
Do not weaken checks merely to make a milestone pass.

---

## 6. Required command interface

Provide working commands with these responsibilities:

npm run dev
npm run build
npm run typecheck
npm run test:unit
npm run test:e2e
npm run assets:inspect
npm run assets:validate
npm run assets:export
npm run test:geometry
npm run evidence:capture
npm run package:source

Each command must perform the stated operation.
Do not create placeholder scripts that always succeed.

Keep expensive asset operations separate from ordinary frontend development.

---

## 7. Milestone reporting and backups

At each milestone, report:

{
  "milestone": "M2",
  "implemented": [],
  "evidenceFiles": [],
  "checksPassed": [],
  "checksFailed": [],
  "checksNotRun": [],
  "reviewPending": [],
  "commit": "",
  "externalBackupVerified": false,
  "blockers": [],
  "nextTask": ""
}

Use real values and evidence.

Record the current state in docs/WORKING_STATE.md so work can resume without repeating completed investigation.

Create checkpoints at meaningful milestones.
I authorize commits and pushes to a separate development branch of the attached repository, excluding secrets and respecting asset licenses.

Do not automatically merge into main.
Do not claim a local commit is an external backup.

---

## Execution rules

1. Start with M0.
2. Implement each milestone as a concrete working result.
3. Do not advance past a failed structural gate.
4. Continue routine work without repeated permission requests.
5. Preserve source assets and existing user work.
6. Do not spend the majority of effort on interface scaffolding before M2–M4 are demonstrated.
7. Do not substitute attractive materials for correct geometry.
8. Do not substitute reports for actual model and animation evidence.
9. If the environment fails, report the actual blocker and recovery state accurately.
10. Do not declare the platform complete while required articulation or anatomy remains unimplemented.

The first substantial deliverable is the M2 resting model:
a convincing external head, coherent internal anatomy, and a true volumetric sagittal cutaway.
