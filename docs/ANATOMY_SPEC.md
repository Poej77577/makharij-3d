# Anatomy production specification

Binding requirements: `IMPLEMENTATION_PLAN.md`; visual reference:
`VISUAL-REFERENCE.ar.md`.

## Frame and provenance

Final browser frame is right-handed, meters, +X anterior, +Y superior, +Z
subject-right. Source coordinate conversions must be recorded and checked
against evaluated exported geometry. M1 studies intentionally store canonical
Y-up mesh data in Blender and export it without a second axis conversion.
Production artist authoring may use native Z-up with an explicitly tested
conversion. Never compensate using an undocumented runtime camera rotation.

Keep upstream artist-authored, medical-research, project-authored and mixed
surfaces distinguishable in provenance. Co-loading does not establish a single
donor. Registration residuals are not measured clinical accuracy.

## Required structures and M2 acceptance

- Complete coherent head, nose, chin, jaw and neck context.
- Continuous perioral skin, volumetric upper/lower lips and natural corners.
- Proper dental crowns with gingival connection; no scan/cast supports.
- Full nonfloating tongue with tip/blade/dorsum/root/lateral margins and an
  understandable mouth-floor attachment.
- Alveolar region, hard palate, soft palate and uvula.
- Genuine oral/nasal/pharyngeal spaces and functional velum relationship.
- Adequate laryngeal context for the intended coverage.

The M1 face study satisfies none of the missing internal-assembly checks by
implication. Fitting cages and color patches must never masquerade as organs
or contact evidence. A physically open context surface must not be treated as
a closed tissue volume by containment or section-cap algorithms.

Visual acceptance requires actual front/side/three-quarter/mouth-close-up,
sagittal and volume-rotation evidence. Mesh statistics and source-byte checks
are supplementary. Independent anatomical and tajwid reviews remain pending.

## Deformation preparation

Keep source topology and source-vertex/region correspondence before editing.
Preserve stable lip loops, mouth lining, tongue volume and intended attachment
boundaries. Bind jaw/teeth/gingiva coherently. Artist control amplitudes are
not clinical ranges. Recalibrate after a changed source, registration or mesh.

Do not start the complete interface or expose the five initial sounds as ready
while this structural gate remains incomplete.
