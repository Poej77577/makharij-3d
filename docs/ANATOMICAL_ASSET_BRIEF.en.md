# MAKHARIJ — Anatomical asset acquisition and authoring brief

## Intended result

A convincing adult human speech-anatomy model for an Arabic teaching platform,
with a coherent external head and actual volumetric oral, nasal, pharyngeal
and laryngeal context. The same model supports external and cutaway views and
independent articulation. This is a source-asset specification, not a claim
that a qualifying asset has already been acquired.

A strong **static anatomical sculpt is acceptable**. It need not arrive rigged.
Retopology, a deformation cage, weights and corrective morphs can be implemented
after the clay shape is qualified. A working avatar rig with weak internal
anatomy is not a substitute for that source shape.

## First delivery: mouth sample before the full head

Supply the actual editable tongue, including dorsal, lateral, ventral and root
surfaces, in context with the oral floor, hard palate and dentition. The free
anterior ventrum must remain distinguishable from posterior/inferior attachment.
Do not replace the root with a hanging bulb, tube or intersection of unrelated
objects. Use one anatomical authoring frame; document any source fitting.

Before a full-head commission or final texture pass, inspect neutral clay views:
isolated side, dorsal, ventral and oblique; then whole-mouth and sagittal context.
Include a topology view and the native file, not only marketplace preview renders.
Any unshown or inferred dimensions must be identified. A silhouette score alone
does not establish anatomy. If the source is static, build the three diagnostic
morphs (tip elevation, dorsum elevation, root retraction) on a copy next. Preserve
the sculpt while testing the deformation cage. These are not Arabic letter poses.

The public-repository modification/redistribution rights below apply to this
sample too. No quote, supplier or qualifying professional sample has yet been
verified. The original procedural tongue pilot was stopped after one correction;
see `TONGUE_PILOT_REVIEW.md`. Do not commission another generic game-head avatar.

## Required anatomical coverage

- A continuous external face with integrated upper/lower lips, cheeks and neck.
- A full organic tongue, including its root and believable connection to the
  oral floor. Preserve dorsal, lateral and ventral surfaces in real 3-D.
- Upper/lower dentition and gingiva, with appropriate hard-palate continuity.
- Soft palate and uvula with deformable tissue thickness.
- Actual nasal passages, septal context and mucosal turbinates; cavities remain
  empty spaces bounded by tissue in both complete and sectioned views.
- Connected nasopharyngeal, oropharyngeal and laryngopharyngeal context,
  epiglottis and appropriate laryngeal/proximal tracheal structures.

Anatomical relationships should be authored coherently. Document source
references and any patient registration claim. A generic authored model must
not be advertised as a scan-registered single patient.

## Deformation architecture

Provide a stable deformation mesh with purposeful edge flow and a separate
high-detail sculpt or non-destructive surface detail where useful. A cage or
surface-deformation layer may drive the presentation mesh. Deliver editable
weights and corrective shapes. Preserve topology after bindings are calibrated.

Required control functions:

- Jaw opening/closing with a documented pivot and coupled lower dentition and
  gingiva; coherent surrounding facial movement.
- Independent tongue tip, blade, dorsum/body, root, lateral and groove control.
  Soft-tissue motion must visibly change shape, including relevant combinations.
- Upper/lower lip opening, closure, rounding, protrusion and lower-lip contact
  with upper incisor edges.
- Soft-palate raising/lowering and uvular coupling, with meaningful changes
  to the velopharyngeal passage.

Controllers can combine bones and shape keys. Export unsupported constraints,
cage effects or drivers by baking a compatible representation. Blender rig
controls alone are insufficient when the exported GLB cannot reproduce them.

## Early acceptance sample

Before final texture work, deliver the actual editable source and a short
neutral-material motion sample showing the following independently:

1. Rest and three-dimensional head rotation, including the tongue/root/floor.
2. Jaw open, mid-transition and return; lower teeth remain coupled.
3. Tongue-tip elevation and return with nonrigid tissue deformation.
4. Dorsum elevation and root retraction/narrowing as distinct controls.
5. Lip closure and lower-lip/upper-incisor contact.
6. Velar raising/lowering with visible port change.
7. Combined jaw/tongue/lip controls, with intermediate-state inspection.

All samples must show the actual asset. Review silhouettes, tissue attachments,
thickness, cavities and contacts at close range and through rotation. Passing
topology or motion-inventory checks does not establish anatomical quality.
These control tests are not automatically approved Arabic articulations.

## Delivery and rights

- Editable `.blend` source, original reference/provenance notes and licensed
  textures, plus the runtime GLB and manifest.
- Meter units, +X anterior, +Y superior, +Z subject right, or an explicit tested
  source-to-runtime conversion. Stable semantic structure and control names.
- A deformation reference set and exported clips/poses with repeatable return
  to rest. Source and browser views must reproduce the same poses.
- Clear rights to modify, author derivatives and use the model in a multiuser
  educational web application. Specify commercial-use rights where relevant.
- Explicit raw-asset/public-repository redistribution permission if the model
  is to be included in this public repository or offered as a GLB download.
  A render-only license or unspecified “royalty free” wording is insufficient.
- Attribution, share-alike and third-party asset restrictions must be documented
  separately from the license of any rigging application or software code.

Do not purchase or commission work on an unverified price or license. Obtain
an exact asset/quote, inspect the permitted source or sample, document rights,
and secure the user's spending authorization before making a commitment.

## Software integration

Keep simulation and authoring offline. The web viewer uses a single Three.js
renderer with synchronized views and one articulation state. Export skeletal
animation and morph targets with corrections; compare the delivered geometry
against the source at intermediate poses, intended contacts and rest.

Initial Arabic targets are ر ق م ف ع after anatomical/control acceptance.
Arabic anatomy and tajweed review is required before classroom claims.
