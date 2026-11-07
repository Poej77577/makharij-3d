# Current implementation state — 2026-11-07

## Latest user direction: rebuild the rejected internal anatomy

The user explicitly rejected the tongue and other internal structures as
unrealistic. Follow `M2_VISUAL_REBUILD.md`. Preserve this mixed-source study as
history, investigate a better coherent anatomical foundation, and rebuild the
inside before adding motion. Passing triangle tests does not override this
visual rejection. Continue alone, without a new permission loop.

Binding request: `IMPLEMENTATION_PLAN.md`. One primary agent; work sequentially.
User directs autonomous problem solving. Do not repeat an optional network
permission loop, add agents, or replace realistic anatomy with primitive organs
or interface scaffolding.

## M0 completed; M1 reconstruction route selected

- Environment works. The earlier outage cause is unconfirmed.
- Preserved legacy commit `103b3a056316664f62c4dffbb09f88b6a6d89a5f`, its Ra
  technical study and the formerly untracked render script. Full Git bundle
  is in `/workspace/artifacts/recovery-2026-11-06`.
- Development branch: `codex/anatomy-foundation-v2`; remote origin is
  `Poej77577/makharij-3d`. Checkpoint `31a0e42d6da9d7ef3937c6c33bb7a7b087bac26e`
  was pushed and its remote hash verified. Later M2 checkpoint/backup details
  are in milestone reports. Do not merge main or overwrite other branches.
- M0 build, source audit, read-only Blender inspection, actual production
  browser pose/return and 16 domain regression tests passed. Those tests refer
  to the preserved legacy inspector, not the new anatomical milestone.
- Selected CC0 MakeHuman adult continuous head, eyes and original controls,
  the inspected Badin oral block and supplementary VKH research context.
- The optional official matching ZIP was denied by the enforced proxy. The
  independently available ArtiSynth reconstruction route removes that
  dependency. No mirror/proxy bypass or new permission request is needed.

## Actual M2 working assembly

`artifacts/milestone-evidence/M2/character-assembly` contains editable source,
actual GLB, evaluated geometry, computed sections and browser/Blender evidence.
It is an **unaccepted M2 working reconstruction**, not the five-letter production
asset. The ordinary app still loads the preserved legacy model.

Implemented:

- Continuous source head/perioral skin and inner oral bag; source body only,
  no visible helper cages. Eyes use original MHCLO barycentric fitting.
- Actual research tongue/crowns/palatal surfaces/velum; old lip patch excluded.
- Actual VKH pharynx, paired suprahyoid muscle context, hyoid and thyroid/
  cricoid cartilage surfaces. These muscles are not a complete mucosal floor;
  cartilage is not vocal-fold or epiglottic coverage.
- Explicit translation calibration plus authored interior mucosa controls and
  shared posterior throat shear. Source bytes are unchanged; mixed donors and
  nominal source scale are acknowledged. See `assets/calibration` and
  `tools/anatomy/surface_fits.py`.
- A rebuilt hollow nasal wall and conchae anchored to the placed palate,
  pharynx and head. The vestibular port stays behind the native nose exterior.
  Septum and bilateral vestibule/choana continuity remain to be completed.
- Actual source TetGen upper-airway reference. A separately authored lower
  continuation uses the observed cricoid opening and an explicit convex upper
  envelope. These are negative spaces, never visible substitute organs.
- Head context has genuine cavity subtraction. Only the explicit neck crop
  receives an artificial closure. Generic context is not segmented brain,
  bone, or a measured tissue reconstruction.
- Closed-volume sections come from delivered GLB triangles. Intentionally open
  crowns/palatal references are not capped. Context sections exclude separately
  represented organ sections so overlapping context cannot conceal an organ.
- Actual browser review uses one renderer, external/section viewports and
  eight camera rotation views. No new articulation or product UI is claimed.

## Reproduction and checks

Use Node 24.19.0/npm 11.9.0, Blender 4.3.2 (CPU, 2 threads), Python 3.12 QA venv.
Requirements are pinned in `scripts/qa/requirements.txt`. Never import those
native wheels into Blender's Python. This Blender build lacks denoising; use
small CPU render batches. No physical-device/GPU performance was measured.

- `npm run assets:export`: full draft fit/negative-space/build/export pipeline.
  Uses committed snapshots and verified source-assembly data, without candidate
  Git checkouts or the optional blocked ZIP. Blender propagates Python errors.
- `npm run assets:validate`: 78 source hashes/notices, 6 tetrahedral boundaries,
  cached-source identity, actual GLB self/clearance checks and the M2 gate.
- `npm run test:geometry`: 6 mesh/section tests, negative-space checks and M2
  gate. The gate returns nonzero while structural tasks remain.
- Diagnostic inspection without anatomical acceptance:
  `.venv-qa/bin/python tools/qa/check_character_assembly.py`.
- `npm run evidence:capture`: actual CPU Blender views and Chromium software
  WebGL review/rotation. Captures are bound to the current asset hash.
- `npm run build`, `npm run typecheck`, `npm run test:unit`.
- `npm run preview -- --port 4173 --strictPort`, then `npm run test:e2e` for the
  preserved inspector; `npm run package:source` for a verified source ZIP.

Thresholds remain fixed. Boolean tessellation produced opposite duplicate
zero-volume fins and submicron slivers during development. The builder removes
exact opposite pairs, uses an explicit 0.1 micrometer numerical cleanup bound
and verifies volume preservation. Preserve inward cavity winding: global normal
recalculation incorrectly inverts enclosed voids. Every subtraction must obey
volume bounds. An earlier sampled-normal nasal floor folded and was rejected;
do not revive it or remove checks to force acceptance.

## Next structural work; do not advance to M3 yet

1. Complete and independently inspect tongue-root/mucosal-floor continuity and
   gingival attachment. Cast-derived gum display bands and the open source
   palatal reference are not final connected production anatomy.
2. Complete nasal septum and bilateral vestibule/choana continuity. Verify
   air-space connectivity and the velum interface instead of assuming them.
3. Review laryngeal inlet coverage and throat placement; add compatible anatomy
   if the intended lesson requires it. Never label cartilage as vocal folds.
4. Finish deformation retopology, material/UV realism and visual M2 acceptance.
   Expert anatomy/tajwid reviews are pending independently of mesh checks.
5. After the structural gate passes, implement a new independent rig and
   recalibrate the five sounds. Old Ra/Mim/Qaf results do not transfer.

No production deployment, main merge, complete Arabic platform, approved sound
library or scientific certification has occurred. Historical diagnostics in
`WORKING-STATE.md` are superseded by this file and milestone evidence.
