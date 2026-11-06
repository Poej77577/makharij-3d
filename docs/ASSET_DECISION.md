# M1 anatomical foundation decision — 2026-11-06

## Decision and gate state

Select the MakeHuman hm08-derived adult head as the **external authoring
foundation**. Its face, lip borders, cheeks and neck are a continuous source
surface with original UVs and source-defined perioral deformation targets.
This is an authored character, not an acquired medical donor.

The combined teaching-anatomy gate remains **pending**. A face-only study is
not the completed M2 resting model. The production inspector still loads the
preserved legacy research-mouth GLB; the new incomplete head is not silently
substituted for it.

## Actual candidate comparison

| Candidate | Files actually inspected | Observed strengths | Blocking limitations | Use |
|---|---|---|---|---|
| Badin/ArtiSynth legacy assembly | Original 30-file licensed snapshot, editable v10 study, complete raw `badinskin.obj` | Actual tongue/teeth/palate research surfaces; published assembly/frame evidence; preserved technical Ra result | Raw skin scan has cropped scalp and neck and no finished external-face topology; old cast-derived gum/lip intersections; no complete larynx | Preserve for research reference and separately verified components; not the finished external head |
| MakeHuman hm08 | Actual `base.obj`, original eye OBJ/MHCLO/texture, facial targets and adult macro targets at pinned commit | Complete continuous head; quad topology/UVs; original facial controls; eyes fit from declared bindings | Matching dental/tongue pack not yet acquired; teaching nasal/pharyngeal/laryngeal assembly absent; materials are study shading | Selected external foundation, subject to completing and reviewing internal anatomy |
| VocalTractLab legacy candidate | Prior actual exported surface audit in `docs/assets/ASSET-DECISION.ar.md` | Original parametric speech controls | Simplified dental arches and ribbon-like lips; no acquired full realistic head in that evaluated export | Historical reference; rejected as delivered visual foundation |

Evidence is in `artifacts/milestone-evidence/M1`. Each rendering records the
actual input hashes and render settings. Badin screenshots are of the actual
raw skin alone; no imagined completion of the cropped scalp was performed.

## License and source evidence

- ArtiSynth: retain the complete research data/software notice and relevant
  academic attribution. Source commit and checksums are in its snapshot.
- MakeHuman: commit `a8bc2d54ff0ac92e78ff71431b1023eda42bf482`.
  Asset file headers and `LICENSE.md` section C expressly release the base
  mesh, targets and eye assets under CC0-1.0. Original notices and the full CC0
  text are included. MakeHuman/MPFB application logic is not copied into the
  product; its separate AGPL license is not mislabeled as CC0.
- A third-party source's name, advertised rig, polygon count or successful
  loading is not anatomical approval.

## Concrete completion approach

1. Acquire and inspect the original matching system teeth/tongue assets,
   including their individual license headers and MHCLO reference bindings.
   Never display the base mesh's fitting helpers as teeth or tongue.
2. Preserve the outer head's continuous lip/perioral topology. Fit matching
   assets against the complete source vertex array before cropping/reindexing.
3. Inspect and complete mouth-floor/root attachment and palatal coverage.
   Do not assume a character tongue is sufficient for Arabic articulation.
4. Reconstruct missing hollow nasal/pharyngeal context with documented
   anatomical references. Any reuse of Badin surfaces requires explicit
   landmark registration, residuals and source/donor limitations. No prior
   Ra/Qaf/Mim calibration transfers automatically to a different head.
5. Complete adequate laryngeal context for the intended sounds; retain pending
   expert-review status. Show genuine empty spaces and actual tissue volumes.
6. Prepare M2 external/internal views and full-volume rotation before accepting
   the model or beginning the production articulation rig.

## Current acquisition blocker

The original 2020 downloader references a now-unavailable separate Git
repository. The publisher's current official website source instead lists:

`https://files2.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip`

Its asset-pack page explicitly lists `teeth_base`, `teeth_shape01` through
`teeth_shape05`, and `tongue01` as CC0. Page source:
https://github.com/makehumancommunity/makehuman-static-website/blob/bc07eb3ac5719e89e0068bb8ee4ea8e38e273e8a/content/Assets/AssetPacks/makehuman_system_assets.md

The download has **not** been acquired. The enforced proxy rejected its HEAD
request with `Tunnel connection failed: 403 Forbidden`. The single primary
download hostname was added to the editable environment network draft,
preserving the six existing custom hostnames. Draft saving does not apply
runtime access or publish the environment. No mirror/proxy bypass was used.

Continue only the independent external-head study until the matching source
can be inspected or another adequately evidenced completion route is selected.
