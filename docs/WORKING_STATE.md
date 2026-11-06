# Current implementation state — 2026-11-06

The binding request is `docs/IMPLEMENTATION_PLAN.md`. This supersedes prior
scope assumptions. Work is sequential, with one primary agent.

## M0 completed

- The executor is connected again. Its previous outage cause is unconfirmed.
- Preserved local HEAD `103b3a056316664f62c4dffbb09f88b6a6d89a5f` and the
  previously untracked diagnostic render script. No prior files were deleted.
- Created branch `codex/anatomy-foundation-v2`. Pushed preserved HEAD and fetched
  it into an independent bare recovery repository. The recovered GLB hash is
  `be34ad893194cc3e192618c89d332916eb5f7976f08617917c94da41e252d6cb`.
- A complete local Git bundle is in `/workspace/artifacts/recovery-2026-11-06`.
- Production build, 30-file source audit, actual browser loading/pose/return,
  TypeScript check, 16 domain-contract regression tests and read-only Blender
  inspection passed. Evidence: `artifacts/milestone-evidence/M0`.

## M1 in progress

The old model is a partial-mouth technical study, not an accepted realistic
external head. Its previous Ra result is preserved and must not be described
as completion of the new M2 or five-letter M4 milestone.

Inspect the actual full Badin skin source and the acquired MakeHuman base mesh.
MakeHuman commit `a8bc2d54ff0ac92e78ff71431b1023eda42bf482` explicitly licenses
its base mesh, eye meshes and deformation targets as CC0 in file headers and
`LICENSE.md`/`LICENSE.ASSETS.md`. Its program code remains AGPL and is not being
copied into the product.

MakeHuman eye OBJ files are not already in the current base-mesh frame: fit
them using their actual MHCLO barycentric bindings and scale declarations.
Do not place them by guessed bounding boxes. Exclude helper geometry from
visible anatomy. Its source `getHeightCm` uses 10 times native mesh height;
one native unit is 0.1 meter.

The old assets downloader references `makehumancommunity/makehuman-assets`,
but that Git operation returned Repository not found; do not claim those
bundled teeth/tongue assets were acquired.

## Commands and boundaries

- `npm run build`, `npm run typecheck`, `npm run test:unit`.
- `npm run assets:inspect -- --input PATH --out PATH` measures real files
  without modifying the input. Default input is explicitly the legacy study.
- Start production with `npm run preview -- --port 4173 --strictPort`, then
  `npm run test:e2e` for the M0 preserved-inspector smoke test.
- Native geometry QA is `.venv-qa/bin/python`; never import its native wheels
  into Blender's Python. The environment is ignored by Git.
- `npm run package:source` packages and verifies approved project directories.
- M2 visual gate, full rig, five new clips, final source validation/export
  commands and release geometry tests remain unfinished. Do not add success
  placeholders for them.
- No main-branch merge or deployment has occurred. No anatomy or tajwid expert
  approval has occurred. Use the source reference image as the visual target.

For historical diagnostics only, consult `docs/WORKING-STATE.md`. Its older
status statements are superseded by this file and the explicit M0 evidence.

## Current M1 result and selected reconstruction route

- MakeHuman snapshot now includes 24 original asset/license files, including4
  source adult macro targets. `python tools/qa/verify_sources.py` checks all 54
  original files across both snapshots plus their audited license notices.
- Selected the external head foundation; complete teaching anatomy is NOT
  accepted. The editable source study and actual exported GLB are in
  artifacts/milestone-evidence/M1/makehuman-adult-head-study/rest. Source/export
  evaluated surface bounds match exactly; no source files were changed.
- A first bounds comparison caught loose source helper vertices retained by
  the head crop. They were removed from the visible mesh; original full source
  coordinates remain in the upstream asset. The corrected export check passes
  without changing its 1 micrometer comparison threshold.
- docs/ASSET_DECISION.md records the actual candidate comparison and missing
  internal assembly; docs/ANATOMY_SPEC.md defines the M2 requirements.
- The matching official system-asset archive is advertised as CC0 by its
  publisher, but has not been downloaded or file-level inspected. Its primary
  host files2.makehumancommunity.org was denied by the enforced proxy 403.
  This one hostname is now added to the network draft, preserving all prior
  custom rules; it is not present in the runtime allowlist. Evidence is
  artifacts/milestone-evidence/M1/matching-assets-acquisition.json.
- The optional matching archive no longer blocks implementation. Independently
  available VKH upper-airway source files were acquired from the permitted
  ArtiSynth repository at its pinned commit. The 20-file unchanged snapshot
  includes its complete license and source load lists. The original blocked
  ZIP was not accessed through a mirror or bypass.
- Source inspection extracts real tetrahedral boundaries for tongue, pharynx,
  aponeurosis and paired suprahyoid tissues; hyoid/thyroid/cricoid are actual
  research surfaces. Inspect their source sagittal and three-quarter views in
  `artifacts/milestone-evidence/M1/vkh-upper-airway`.
- Continue M2 using the continuous head, prepared research oral block and
  separately documented VKH context. Initial translation-only authoring fits
  are in `assets/calibration/character-fit.json`. They are not clinical or
  single-donor registration. The old lip-context mesh is excluded.
- `tools/blender/character_assembly.py` produces an editable combined source,
  actual GLB, evaluated geometry and diagnostic views. Oral lining,
  pharyngeal/floor attachment, nasal fit and gingival continuity still require
  real geometric and visual work before M2 acceptance. No new rig is claimed.
