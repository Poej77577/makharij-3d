# Bounded nasal airway QA

The runtime positive mucosal wall, closed negative air envelope, and external
head triangle surface are separate inputs. An air-envelope label or guide
curve is not a pass: actual exported geometry must validate each test.

## Stable invocation

```sh
.venv-qa/bin/python tools/qa/nasal_airway.py --self-test
.venv-qa/bin/python tools/qa/nasal_airway.py \
  --folder artifacts/method-evidence/nasal-cavity \
  --face-folder artifacts/method-evidence/face-context --gate
```

Actual-asset output: `qa/nasal-airway.json`. Gate identity fields are `passed`,
`assetSha256` (runtime wall), `airAssetSha256` (analysis air), and
`faceAssetSha256` (actual external face). Replaced reports are archived under
`qa/history`; analytical fixture results cannot act as an asset gate.

## Geometry contract and checks

- Runtime `nasal-cavity.glb`: positive `NASAL_MUCOSA`, optional positive
  `NASAL_SEPTUM`; no renderable negative air solid.
- Analysis `nasal-airspace.analysis.glb`: one closed connected
  `NASAL_AIR_NEGATIVE` envelope, not runtime tissue.
- `nasal-manifest.json`: canonical `gltfToProject`; three `ports` with `id`,
  `role` (two inlets, one outlet), `center_m`, unit `inward_normal`, and
  `ring_vertex_positions_m`; two `guide_paths` with `inlet`, `outlet`, and
  `points_m`. Both paths end at the same outlet centre.
- Blender imports the actual three GLBs into one frame, clears animation and
  morph weights to rest, and exports evaluated world positions. No source
  mesh is edited.
- Closed air and each positive wall must have finite valid geometry,
  watertight consistent winding and positive volume. The combined runtime
  wall must be one connected genus-2 surface (Euler characteristic -2); the
  air envelope must be one connected genus-0 surface (Euler characteristic 2).
  These are mandatory checks, independent of sampled boundary coverage. Only the air envelope
  may define negative air. Wall membership is checked against wall volumes;
  the external head is never treated as a volume.
- FCL swept capsules of radius **0.25 mm** test every guide segment. This
  tests continuous segments, including obstructions between sampled points.
  Interior guides must remain within the closed negative envelope and outside
  all positive walls. The reported radius is a geometric corridor lower
  bound along those guides, not the largest possible lumen radius or a
  clinical threshold.
- Each actual port must have an inward probe inside air and an outward probe
  outside air, a centre at the air boundary, and a ring attached to mucosa.
  Inlet rings must also match actual head boundary vertices. A separate
  capsule bridge crosses each opening against positive mucosa and the head
  surface. Artificial negative-air end caps are excluded only from this
  opening test; a real tissue/head cap remains an obstacle.
- Up to 1024 negative-air boundary triangle centres are checked against the
  positive wall. Uncovered samples outside the measured port regions fail;
  this bounded coverage check is not an exhaustive micro-leak audit.

## Analytical fixtures

The exact rectilinear fixture has two anterior branches separated by a
septum, a shared posterior chamber, and one posterior outlet.

| Geometry | Expected result |
|---|---|
| Open bilateral lumen with positive surrounding walls | Both routes and all openings pass |
| Solid slab across only the left branch, between sampled guide centres | Continuous stroke detects it; left fails and right stays clear |
| Open two-triangle surface covering the left opening | Opening fails without using head containment |

Results are stored in `analytical-fixtures.json`. These fixtures validate
diagnostic behavior; they do not approve any anatomical asset.

The actual gate is limited to the three rest-state openings, two tested
geometric corridors and sampled wall coverage. It does not validate CFD,
physiology, nasal turbinates/sinuses, motion, optimal cross-sectional areas,
all alternate routes, clinical anatomy or expert educational acceptance.


## Corrected actual candidate

The strict geometry gate passes with wall genus 2 and air genus 0; each is one connected, watertight, consistently wound positive volume. Both inlet paths contain 77 tested segments, all three physical opening bridges are clear at a 0.25 mm probe radius, and inlet rings match the actual face boundary. Minimum physical-surface centreline clearance is 1.101 mm; the 0.934 mm analysis-end-cap limit is separate from physical tissue.

- assetSha256: `db86baa8e1ac86d576ef0dee27ca8eeb687d016f09544e7960dbd1f6214bc554`
- airAssetSha256: `871524951f2f24215d93d6bf2f5a011948e9d60c35547a38eb8634b4a30f81d1`
- faceAssetSha256: `dce24684c15a7a18683f55beee17609a97330ce86de7dec61429c3db1305cf94`

The earlier a91dc0db candidate had wall genus 4 and is rejected. Its route-only pass is superseded explicitly in the history failure report; the original report bytes remain in superseded-route-only-report.json. topology-regression.json verifies the actual old cached geometry fails and the corrected actual geometry passes. Analytical rectangular-wall corridor fixtures intentionally disable the monolithic-shell topology requirement; separate box/torus fixtures verify Euler/genus computation. Actual-asset mode always enforces it.

Full results: nasal-airway.json; concise results: nasal-airway-summary.json. This QA evaluates rest with all exported morph weights set to zero. Independent morph/collar-follow work is separate. Attribution and source terms are in the parent NOTICE.md.
