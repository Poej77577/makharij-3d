# Selected external-face/dental surface review

`face-contacts.json` records the actual current face and oral GLB hashes.
Ten states and twenty pairs passed without triangle-surface crossings or
contact-budget saturation. The minimum surface separation is 5.615 mm, at
half lip compression versus the upper left lateral incisor. Per-pair nearest
witness points and actual maximum movement are retained in the report.

The evaluator imports both GLBs into a clean Blender scene and applies one
shared jaw state: the face receives its authored morph once, while only the
oral lower dental pivot rotates rigidly. All three lip controls are checked
at half/full weight, jaw at half/full weight, rest and one half-weight combined
jaw/lip pose. Upper teeth remain fixed; lip-only poses leave lower teeth fixed.

**The external head is an open surface.** FCL checks triangle intersections and
true nearest-surface distances only. No containment, signed solid distance,
head volume, tissue thickness or penetration depth is computed or claimed.
The open-plane/box analytical fixture in `open-surface-self-test.json` checks
known separation and crossing independently of the anatomy assets.

The report does not assess every combination, self intersections, tongue/skin,
lip/gingiva or palatal contact, biomechanics, anatomical beauty or Arabic
articulation. A zero-crossing result is not a phonetic-contact validation.

```sh
.venv-qa/bin/python tools/qa/face_contacts.py --self-test
npm run assets:face:contacts
npm run assets:face:stage
```

Staging requires both matching hashes and all ten states/twenty pairs. If a
different pair of GLBs is checked, the tool retains earlier evidence in a
separate hash-named folder. Source rights and attribution remain in
`../NOTICE.md` and `../../oral-sculpt/NOTICE.md`.
