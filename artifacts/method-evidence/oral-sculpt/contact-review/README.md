# Tongue/dental contact review

This is a selected engineering contact check of actual evaluated GLB geometry.
It is not a visual, anatomical, phonetic or clinical approval.

## Baseline finding

Input GLB SHA256:
`e22cafd412a2928a1d002d8a1d1c437bf34bdc793eb27d43cfb8dcc13e42ba00`.

The 18 inspected states produced 36 tongue/dental-arch pairs. Seventeen pairs
had crossing surfaces, all against the lower dentition, without reaching the
4,000-contact cap. Rest/return had 1,208 FCL triangle contacts. An independently
tested tooth-surface sample lay 4.680 mm inside the closed tongue, measured as
its nearest distance to the tongue surface. The witness was near the right
lower medial incisor at canonical `[-14.390, -7.092, +2.042] mm`.

The upper dentition was separated at rest by 5.534 mm. The original `all_max`
state was clear even though rest and many intermediate states crossed: testing
only controller extremes would have missed the defect.

`rest-contact.png` and `worst-contact.png` are scientific projections of actual
mesh samples and crossing witnesses. They are not shaded medical illustrations
and do not imply depth occlusion. The GLB/native source meshes were not edited
by the checker; exported evaluated geometry remains in a research cache outside
the product repository.

## Corrected candidate

The separately authored candidate at `../next` with GLB SHA256
`40e2bd2303abbd250771fcd617f572e54a6b9e8da573a24d4881cabb07af7bea`
was checked over the same 18 states and 36 pairs. No surface crossings or tested
interior samples were found, and no contact cap was reached. The smallest
selected separation was 2.324 mm for full tip elevation against lower teeth.

`baseline-candidate-comparison.json` records both identities and the bounded
comparison. Detailed candidate results and projections are in
`../next/contact-review`. A changed/rebaked GLB needs its own identity check;
these findings do not automatically transfer to a different asset hash.

## Final baked delivery

The current baked GLB is
`e051e47ad424a3d301f12acd75325998d6079007c3babd78175a31bbf563e0c6`.
It was independently re-evaluated after material baking: 18 states/36 pairs,
zero crossings, zero saturated pairs and minimum separation 2.324 mm. The
matching final report, projections and baseline comparison are in
`e051e47ad424a3d3/`. Staging requires the current GLB hash and the full selected
18-state/36-pair report, so the raw candidate's pass cannot stage a rebaked GLB.

## Measurement semantics

- Official Blender GLB import evaluates the actual morph targets, explicit
  product-weight corrective shapes and rigid jaw transform. Geometry is
  converted to metres, +X anterior, +Y superior, +Z subject right.
- FCL checks triangle surface intersections and minimum separation. Contact
  counts are reported as supplied by FCL, with saturation flagged. Negative
  FCL distances and its triangle contact penetration values are not used as
  solid penetration depth.
- Finite dental/tongue surface samples are classified inside an opposing closed
  mesh; their nearest-surface distances quantify sampled intrusion separately.
  The reported maximum is a lower bound over the tested sample set, not exact
  maximum penetration depth or intersection volume. Sampling sets may differ
  between poses, so the values are not a precise depth-versus-control curve.
- UV/normal seam duplicates are welded at 1e-10 m for topology/containment only;
  vertex positions and triangle surfaces are preserved to that tolerance. Dental
  component labels match original source vertices; multiple disconnected parts
  may belong to one tooth. Label samples and maximum/mean residuals are recorded.
- Near-touch is separation no more than 0.2 mm. Surface crossing still needs
  review even when sampled interior distance is under the 0.1 mm threshold.
  This tool does not decide whether a phonetic contact is intended.

`lingual-boundary-samples.json` contains actual lower-arch +X ray hits at selected
heights and transverse offsets. They demonstrate why a single anterior X limit
cannot fit the whole tongue. They are not a continuous clearance envelope.

Not checked: gingiva, palate, mouth floor, head skin, whole-surface self
intersections, every combination, biomechanics or Arabic articulation. A dental
clearance pass cannot approve shape, tissue insertions or teaching readiness.

## Reproduce

```sh
.venv-qa/bin/python tools/qa/oral_contacts.py --self-test
.venv-qa/bin/python tools/qa/oral_contacts.py --asset artifacts/method-evidence/oral-sculpt/baseline-contact.glb --manifest artifacts/method-evidence/oral-sculpt/baseline-contact.manifest.json
.venv-qa/bin/python tools/qa/oral_contacts.py --folder artifacts/method-evidence/oral-sculpt/next --gate
npm run assets:oral:contacts
```

The analytical self-test checks known box separation and inside-surface distances,
including complete containment, independently of the anatomy asset. The default
checker is diagnostic; `--gate` fails when the selected dental clearance is
unresolved. Optional `--case`, `--cases`, `--samples` and `--contact-limit` keep
targeted rechecks bounded. Do not lower the budget silently to declare clearance.
If a report already exists for a different GLB hash, a new hash-named subfolder
is used and the final report path is printed. A default current-asset check must
not overwrite this preserved baseline defect report.

Geometry provenance/rights are unchanged: BodyParts3D / DBCLS / Kousaku Okubo and
Z-Anatomy / Gauthier Kervyn, with the project's CC BY-SA 4.0 model-data terms.
See `../NOTICE.md` and `assets/source/z-anatomy/NOTICE.md` for full attribution.
