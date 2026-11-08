# M1 anatomical foundation decision — 2026-11-06

## Face context and contact correction — 2026-11-08

The user authorized continued work with a third team member. A separate
original MakeHuman external face and three lip morphs now accompany the oral
prototype; see `FACE_CONTEXT_REVIEW.md`. The rejected atlas/Boolean head was
not reused. One state drives the facial jaw shape and the rigid dental pivot.
The independent reviewer found and verified a real oral dental-intersection
fix (17/36 crossing pairs before, zero in the selected final pairs). These
checks do not accept the still-generic tongue/root/palatal form. A qualified
internal sculpt and expert review remain required before teaching use.

## New user-authorized oral study — 2026-11-07

After the bounded loft failed, the user explicitly requested improvement with
advanced skills. A separate continuous surface / nonplanar floor / cage study is
implemented on `/mouth.html`; see `ORAL_SCULPT_REVIEW.md`. It is an experimental
oral unit with technical evidence, not a selected complete head or an anatomy
acceptance. The rejected states below remain unchanged.

## Latest rejection and method change — 2026-11-07

The user has now rejected the atlas rebuild as well. The following selection is
withdrawn as a production visual foundation. Follow `ANIMATABLE_ASSET_ROUTE.md`
and the deformation-ready asset brief. Keep the old meshes for comparison;
passing numerical checks does not reset the user's rejection.

The subsequent original section-authored tongue pilot also failed its bounded
clay gate after one revision. See `TONGUE_PILOT_REVIEW.md` and the independent
agent critique. A qualified static anatomical sculpt is an acceptable next
source; a complete pre-existing rig is not required. No new visual source is
selected. Preserve the failed pilot only for mechanical export tests.

## Historical superseding decision — withdrawn, 2026-11-07

The user rejected the mixed-source M2 interior. The active reconstruction uses
75 actual selected Z-Anatomy / BodyParts3D mesh structures in their common
source frame, with documented tongue/root and tissue refinements. See
`M2/realistic-rebuild`, `assets/source/z-anatomy/NOTICE.md` and `WORKING_STATE.md`.
The real archive, native units and extracted geometry were inspected; source
publisher renders alone were not used as acceptance evidence. Adaptations
require CC BY-SA 4.0 and original attribution. Separately licensed inner-ear,
kidney and brain content is excluded.

The CC0 MakeHuman continuous outer head is retained, with an authored oral
vestibule fit and one dental atlas translation. This is not patient registration.
Visual/expert acceptance remains pending. The decision below records the
**rejected historical study**, not the current internal asset choice.

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
| VKH upper airway / ArtiSynth | 24 unchanged licensed files, source load lists, five tetrahedral soft-tissue boundaries, five rigid surfaces and WA TetGen airspace | Actual volumetric tongue, pharynx, palatine aponeurosis and suprahyoid tissues; hyoid, thyroid and cricoid surfaces | Independent donor/frame; maxilla and mandible include bone; aponeurosis is not a complete uvula; no matching external-face rig | Selected supplementary research foundation for documented reconstruction |
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

1. Use the already inspected research dental crowns, tongue and palates with
   the selected continuous head. Supplement pharynx, suprahyoid and laryngeal
   context from the licensed VKH source assembly. Matching MakeHuman assets
   are optional; their denied download no longer blocks this approach.
2. Preserve the outer head's continuous lip/perioral topology. Fit matching
   assets against the complete source vertex array before cropping/reindexing.
3. Inspect and complete mouth-floor/root attachment and palatal coverage.
   Do not assume a character tongue is sufficient for Arabic articulation.
4. Reconstruct missing hollow nasal/pharyngeal context with documented
   anatomical references. Any reuse of Badin surfaces requires explicit
   authoring placement, fit measurements and source/donor limitations. No prior
   Ra/Qaf/Mim calibration transfers automatically to a different head.
5. Complete adequate laryngeal context for the intended sounds; retain pending
   expert-review status. Show genuine empty spaces and actual tissue volumes.
6. Prepare M2 external/internal views and full-volume rotation before accepting
   the model or beginning the production articulation rig.

## Optional matching pack: access history

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

The reconstruction route above was subsequently selected using independently
available assets in the permitted ArtiSynth repository. No change to runtime
access or further attempt at the denied archive is required for this work.

## Initial reconstruction fit

`assets/calibration/character-fit.json` records translation-only placement at
an actual anterior dental edge and the character's invisible fitting-reference
edge. Scale and rotation are preserved. This is an artist placement method;
it does not establish clinical alignment or common donor identity. The old
oral block and new VKH context receive separate recorded transforms.

The reproducible M2 working assembly is built by
`tools/blender/character_assembly.py`. Its actual source/export files and views
are in `artifacts/milestone-evidence/M2/character-assembly`. Oral mucosa,
gingival continuity, nasal reconstruction and attachment/clearance checks
remain explicit M2 tasks. Earlier Ra and Mim results do not transfer to it.

The later M2 throat-context posterior shear and oral-mucosa controls are
recorded in the assembly manifest and `tools/anatomy/surface_fits.py`. They
are authored fits after the initial translation, not measured registration.
The nasal wall is rebuilt against the newly placed palate/pharynx/head. Its
negative-space helper, the actual upper-airway reference and a separately
authored cricoid-guided lower continuation form genuine 3-D voids in the head
context. Bone/cartilage and acquired soft tissues retain their own provenance.
