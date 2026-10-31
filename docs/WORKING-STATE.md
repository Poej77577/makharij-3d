# Continuation state — do not restart or repeat broad validation

User goal: full Arabic Makharij anatomical 3D platform, all letters, actual acquired anatomy, nonrigid controls, phased gates, no primitives/fake claims. Latest instructions: keep working; reduce agents/credits; use their sagittal atlas image as visual target. At most coordinator + ONE anatomy agent. Currently only coordinator works; anatomy agent finished its frozen module. Do not restart six-agent parallel work or stop at acknowledging a reference.

## What actually works

- Acquired/audited VTL and ArtiSynth; selected Badin/ArtiSynth, no primitive mouth. Compact licensed source snapshot assets/source/artiSynth: 30 original files, manifest + SHA; verify_selected_source.py passes.
- Current source build: scripts/anatomy/build_rest.py, continuous_lips.py, refine_lip_contacts.py, nasal_lining.py, trim_nasal_interface.py. Blender4.3.2, source units m, Xanterior/Yup/Zlateral, canonical transform x=.14-nativeX,y=nativeZ-.1,z=nativeY.
- Current prepared REST is v10, 13 meshes. Continuous FEM LIP_CONTEXT4957v9143t after conforming edge refinement (shape unchanged), original lip region masks in rest JSON/masks file. No old separate filled lip objects. Original source bones/teeth real crowned cast surfaces, scan support removed with documented slope. Nose has authored UNMEASURED wall +3 conchae; C-shaped posterior opening leaves actual velum as moving boundary. Nasal wall trimmed against .15mm outward-offset acquired velum to remove an actual4.5mm overlap. Final v9 nasal15pair checks clear; v10 only refines coplanar lip triangles.
- Public app is technical inspector + actual Ra prototype; NOT finished student platform. Main asset public/models/makharij-ra-prototype.glb currently uses v9 rest (lip2459), physically same unrefined surface as v10. Source GLB assets/anatomy/makharij-ra-prototype.glb, editable animated .blend.
- Actual Ra uses TWO GPU morphs: ra_prepared (7mm artistic tip retraction before lift), ra_contact (staged actual source-derived lift). Actual exported GLB independently checked104states×12obstacles with zero intersections, min triangle area ratio .278, intended alveolar ROI gap .133mm and4 near vertices. Report research/qa/ra-glb-v9.json. No tafkhim/tarqiq calibration or scientific review claimed.
- Browser production build: no JS errors; rest/peak canvas differs and returned pose equals rest; complete recorded cycle via actual canvas at0.25×, software SwiftShader, no hardware performance claims. Latest evidence research/qa/ra-runtime-v9 (folder copied from last v6-named run; hashes identify actual v9 model). Latest video /workspace/artifacts/ra-reference-prototype.webm. Historical /workspace/artifacts/ra-v6-prototype.webm remains older nasal anatomy.
- Computed tongue section cap uses actual deformed volume stencil, procedural illustrative fiber material (not acquired muscle data). Full volume mode removes cap. Camera faces LEFT to match user reference. One renderer, two synced views, actual orbit/zoom/pan, swap/focus/highlight/labels/visibility/fullscreen. Main model shape still does not fully match atlas; no anatomy gate claim.

## Active unsolved work (do not claim passed)

Qaf:
- data/motion/tongue-fit-qaf-v6f: safe smooth local field, actual velum ROI gap .120mm,3near vertices; all65path samples clear, area ratio .994. Parameters centreX25.32mm,widthX5.5, centreY6.2,widthY6.5, deltaX-5.46,deltaY5.84, Zgaussian14mm^4. This proves central contact only; transverse closure still unverified. NOT active in UI.
- qaf-contact-band-v6 and qaf-surface-v10 are FAILED wider-band attempts. The ARAP version matches the band well (.15mm-ish) but PHARYNX collision starts .625 and HARD_PALATE late. Existing fixed set7382 of8834 tongue vertices; next possible correction is active-set pins for actual colliding non-handle triangles, not arbitrary shading. Need final whole-path actual GLB testing before public/gate claim.

Mim:
- No working public Mim yet. Old v4 failed lip gap5mm. Static lip ARAP latest mim-surface-v10b: some small/large gaps, self intersections and path failures. Do NOT integrate.
- Jaw-coordinated approach is more anatomical: prepare_mim_jaw.py samples swept lower crowns for jaw+6deg (restjaw=-6). Smooth positive radial tongue relaxation needed only .177mm, area ratio .957, all target tongue/bone/palate pairs clear. It uses geometric radial envelopes, not muscle physics. Source data/motion/mim-jaw-v10/targets.npz.
- fit_mim_joint.py: actual moving jaw/lower teeth + continuous lip ARAP; central closure mostly .1-.26mm, but upper/lower dental intersections and late triangle area <.1. NOT passed. Current anchors move with analytic weighted jaw and may overconstrain cut-boundary cheek vertices. Potential next steps: relax intermediate jaw-weight boundary anchors; use positive smooth outside-dental-envelope map for lip family, or collision active-set constraints. Do not flatten/project arbitrary individual vertices (previous tongue clipping caused folds).
- SurfaceArap utility scripts/motion/surface_arap.py exists. Lip contact matrices use actual triangle-plane barycentric handles. Source upper/lower masks have shared corner tissue, so naive whole-mask self-contact counts can include legitimate adjacency; central independent parts still checked.

## Important files/tool details

- Main src/main.ts/viewer.ts/ra-prototype.ts/styles.css, index.html. src/motion.ts is OLD failed5pose sampler, not active runtime. Do not expose its aliases as passed.
- data/content-review.json32 draft settings + actual Jazariyyah excerpt sources docs/content. No licensed audio or verified Quran examples, no Jordan textbook access. Audio must stay pending, no TTS as accredited recitation.
- QA Python dependencies in /tmp/makharij-qa-deps; normal Python3.12 supports trimesh/fcl/rtree/scipy. Blender Python3.13 cannot load those native wheels; Blender exports then normal Python QA.
- Browser /usr/bin/chromium + Python Playwright, needs supported require_escalated command due sandbox syscall restrictions; SwiftShader only. Production preview4173 running (restart if absent). Do not present localhost links to user.
- Source sparse GLB morph accessors supported by scripts/qa/check_ra_glb.py. It currently checks R and expects exactly Rtwo targets; update deliberately if adding other real morphs. It evaluates actual decoded exported positions, not undeformed Trimesh base.
- build_rest changes rest SHA. export_ra_prototype.py refuses mismatched fit SHA. Inherit a fit only after explicit proof relevant source geometry unchanged; document lineage. V10 lip is a retessellation, so compare actual surfaces, not raw counts. Revalidate final exported GLB against new anatomy.
- Source checkpoint package script scripts/package_source.py writes ../artifacts/makharij-source.zip; package is WIP. No Git push or deployment. All files still untracked in main checkout; local commit/checkpoint appropriate once no jobs mutate source. Ignore Blender .blend1/.blend2 backups, candidate checkouts, research caches.
- Saved environment draft install/start instructions exist for technical inspector only; saving not publication. No Sites deployment tools available. Do not invent a link or site ID.

## Latest continuation: 31 October 2026

- Qaf active-set attempt `qaf-surface-active-v10` failed: pinning 70 actual blocking vertices removed pharynx/hard-palate collisions but prevented lateral closure (up to 8.96 mm gap), and late velum penetration remains. It is not integrated.
- Mim jaw4 `mim-joint-v10b` failed at eight late states against lower teeth, and central upper/lower self-contact occurred. Its historical unexecuted prep checks are explicitly null/unrun, never interpreted as passed.
- Mim free-border variant `mim-joint-v10c` also failed.
- `mim-clearance-v10` smooth separation removed central lip/lip intersections at all79 sampled states/midpoints, but lower-teeth contact and low triangle area remain. Gingiva intersections already occur at rest and need attachment/vestibule review, not silent exclusion.
- `relax_mim_clearance_b.py` is a further candidate using a positive horizontal affine clearance map, preserving embedding rather than radial compression. No pass is claimed until its report and final exported geometry are checked.

- Current delivered Ra is now v10 refined lip mesh, SHA be34ad893194cc3e192618c89d332916eb5f7976f08617917c94da41e252d6cb. Explicit geometric inheritance is recorded in data/motion/tongue-fit-ra-v10. Final GLB104×12 checks passed with unchanged contact/area metrics. Caps now cover all6 closed tissues with independent stencil clearing, not open surfaces. See docs/validation/CONTINUATION-v10.ar.md.
- Mim local collision-normal ARAP correction (mim-local-contact-v10) is more promising: all79states/midpoints teeth and central upper/lower pairs clear, minarea .216, closure64sections .042–.441mm. Gum intersections remain (including rest); nasal velum motion still absent. NOT a completed Mim or public motion.
