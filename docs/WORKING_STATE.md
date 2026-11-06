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
