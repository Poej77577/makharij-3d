# Bounded roof/gingiva candidate — integration contract

Final helper: `tools/anatomy/oral_roof_refinement.py`. It is Blender-only and uses project metres, +X anterior/+Y superior/+Z subject right. It does not write files or touch global objects. The research master is `roof-gum-candidate.blend`; `source-and-proposed-points.npz` preserves the original and proposed gingival coordinates and identical source faces.

```python
from oral_roof_refinement import refine_gingival_ends, make_posterior_soft_palate
new_upper_points, upper_meta = refine_gingival_ends(
    upper_points, upper_faces, upper_teeth_points, upper_teeth_faces, 'upper')
new_lower_points, lower_meta = refine_gingival_ends(
    lower_points, lower_faces, lower_teeth_points, lower_teeth_faces, 'lower')
roof_points, roof_faces, roof_meta = make_posterior_soft_palate(
    new_upper_points, upper_faces)
```

1. Apply the local gingival point changes before objects are parented/rigged. Preserve source faces, vertex IDs and UV mapping. Lower gingiva stays a rigid child of the existing jaw. Indicate these local modifications in source provenance and retain BodyParts3D/Z-Anatomy attribution and CC BY-SA model-data obligations.
2. Remove the old authored anterior hard-palate plate. Keep the original upper-gingival mucosal surface in its original semantic role; it provides anterior palatal mucosal context. It is not hard-palatal bone and must not be relabelled as one. New `PALATE` is an authored posterior soft-palate/uvular tissue volume. Its source-anchored geometry is not a CC0 asset claim.
3. Do not add Subdivision or copy old `VELUM_RAISE` keys onto the new topology. The returned 48x48 grid is already sampled densely. `deformationGrid` gives `verticesPerLayer=2401` and 49 columns. Before baking, for vertex `i`, `u=((i % 2401)//49)/48` and column `j=(i % 2401)%49`. Use the actual attachment source/proposed row for pivots. Pin the anterior ~15% and smoothly raise the posterior portion, then bake a fresh compatible morph. The first row must remain fixed under every velum value.
4. Regenerate the combined native/export/manifest and recheck actual poses: rest, velum half/max, jaw half/max, jaw+velum, dorsum+velum and root+velum. Compare source and GLB at intermediate values, then repeat contact checks against the new tongue/floor candidate. This subtask checked only rest geometry against the frozen baseline.
5. Reuse the same fixed-camera clay views for final visual review. Two separate closed volumes overlap deliberately in the 1.5-mm attachment strip; they are not welded. Co-planar sagittal caps may z-fight at this interface, so inspect whole surfaces and the interface samples before treating a dark cap pixel as an air gap. Do not hide that overlap or claim a unified mucosal mesh.

## Completed evidence

- New soft volume: 4,802 vertices/4,800 quads, closed, positive volume, no edge-incidence nonmanifold or degenerate triangles.
- FCL nonadjacent self contacts: zero for new soft palate and both gingivae; enumeration unsaturated. The invalid normal-offset construction was rejected and its failed diagnostic retained separately; the final superior graph-offset thickness has minimum local normal projection ~0.894 mm after the source-thickness attachment clamp.
- Actual gum/tooth triangle contact pair sets unchanged from source: upper 3,253; lower 3,126. Existing anatomical source overlaps remain, so this is not a no-collision or biological-contact claim.
- 6,568 tooth-near source vertices pinned exactly. Lower posterior maximum height reduced from 16.07 to 10.80 mm in the unchanged source frame; all source triangles preserved. Upper maximum deformation ~0.49 mm and lower ~6.87 mm. Both have zero inverted source triangles.
- 147/147 sampled front-interface points (lower, upper and mid-cap) classify inside the closed upper-gingival source, with no sampled outside point. The lower-row maximum nearest-surface offset from the independent check is ~0.167 mm. This is finite evidence of an overlapping junction, not an all-surface guarantee or clinical registration.

## Evidence files and limits

`candidate-report.json`, `interface-check.json`, `self-contacts.json`, `roof-comparison.png`, `gingival-comparison.png`, and `source-and-proposed-points.npz`.

I visually inspected both before/candidate roof inferior and source-section images and both lower oral-context images. The duplicated authored roof and posterior gingival fins improve. Posterior/lateral sample edges and free-edge/uvular shaping remain inferred; no complete pharyngeal pillars or nasal/velopharyngeal port have been authored, and no medical or Arabic articulation acceptance is implied. No further authored geometry changes are proposed in this bounded subtask.
