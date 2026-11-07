# Independent method review — 2026-11-07

## Decision

MB-Lab has real quad oral geometry and real external tongue morph data; it is not a clinically complete internal speech-anatomy asset. Do not adopt it as MAKHARIJ's final tongue/root/floor/soft-palate source. The model database is AGPL-3.0-or-later, not CC0. AGPL itself is not an automatic exclusion, but requires a separate deliberate rights/integration decision.

Exact source evidence and limitations: `mb-lab-findings.json`. Source commit: `063bff04e60f3e7c651fda628c30f5d83f3f3078`. Original asset files remain outside the product repository. This retained report uses local evidence filenames; findings are unchanged.

## What was actually verified

- Official native library: 17,680,712 bytes, SHA256 `ae2a03430be1ef0f74a9bfa01136579e88beb521c9db7d496b5921bec6d1cd4e`.
- `MBLab_human_male` contains `MBLab_tongue` as a material region, not a standalone tongue object: 114 vertices, 112 quads, 0 boundary edges and 0 edge-incidence nonmanifold edges.
- Same-frame `MBlab_human_teeth`: 3,475 vertices, 3,422 polygons, 106 boundary edges. Named separate floor/palate/velum/root objects were not found.
- Eight actual tongue morphs in the 3.6 MB `m_ca01_exprs.json` affect 73–114 tongue vertices each, with no vertices outside the tongue region. Driver JSON maps TipUp to expression and TH/L phoneme controls. Raw library objects have no instantiated weights or shape keys. We did not execute or export these morphs, and therefore do not claim a tested runtime rig.
- `morphengine.py` replaces library coordinates using `m_ca01_verts.json`. That actual base file was checked: all 114 tongue coordinates match the library within 5.99e-8 native units; the profile is not an uninitialized-template artifact.
- Clay images inspect the actual source shape with no sculpt, remesh or invented anatomy. The region has an oval ventral plate and C/fork profile. The split points anterior in same-frame dental context; the initial isolated-view direction assumption was corrected.

## Why the previous approach failed

Meshes from atlases, numerical closure, hole filling and a skin shell did not supply a coherent artistic anatomical design. Topology and collision checks validate narrow computational properties. They do not validate a tongue silhouette, root/floor continuity or tissue identity. Textures and microdetail cannot repair that missing design. Conversely, requiring a complete already-rigged anatomical asset was unnecessarily restrictive: a good static sculpt can be retopologized and rigged.

## At most two practical paths

1. Build one original bounded tongue/floor/palate clay pilot now. Design sagittal and transverse silhouettes, author one continuous tongue surface with a meaningful free anterior/ventral surface and posterior/inferior attachment, then add tip, dorsum and root morphs. Render isolated top/side/ventral views and same-frame dental/palatal context. Fix topology before morphs; do not add papillae or final shaders first. Baseline plus one targeted anatomical correction is the budget. If the result still reads as an egg, plate, tube or ambiguous root, stop considering it a production base.
2. If the pilot fails that visual gate, obtain or commission a coherent anatomical sculpt and retopologize/cage-rig it. The source need not arrive rigged. Actual file/license inspection and artist/anatomy review are necessary. No qualifying professional file has been inspected in this subtask, and no purchase is justified by marketplace previews.

## What code alone does not solve

Anatomic silhouette design, the ventral/root/floor relationship, soft-palate thickness and attachment, and artistic surface shaping need explicit modeling judgment and reference review. A 2D atlas image does not determine hidden 3D tissue. A Blender API skill or MCP bridge runs operations; it does not manufacture missing anatomy or validate it. Arabic articulation poses also require appropriate phonetic/tajweed review before classroom claims. Browser control and GLB morph playback are implementable once the source shape and motion have passed those gates.
