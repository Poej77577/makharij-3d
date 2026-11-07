# Native deformation-route investigation

These reports contain source identities and measured observations. The original
candidate geometry is **not redistributed**: its complete asset license has not
been established. It is not a selected or accepted MAKHARIJ anatomy model.

`research-sources.json` records primary repositories, exact inspected commits,
license observations and limits. `access-observations.json` records the actual
CONNECT 403 failures for the professional-source search. A saved network draft
has not changed the running destination policy.

## Actual Blender file inspected

- Publisher: https://github.com/m2ci-msp/ematoblender-model/releases/tag/v0.1
- File: `ematoblender-model.blend`, 2,491,956 bytes, Blender 2.76 source.
- SHA-256: `b567ded59157db012927d68d44d16fc6f90b214bfb238b975bcdcb8ad3dedef7`.
- The recorded hash identifies the actual inspected download; it is not a
  separately published vendor checksum or a scientific endorsement.
- Loaded in Blender 4.3.2 with embedded script execution disabled.

`ematoblender-rig-audit.json` records actual bones, constraints, modifiers,
weights and shape keys. The face has an Armature binding; the tongue and
palate do not have independently bound controls in the inspected file.

`ematoblender-jaw-probe.json`: an 8-degree Jaw rotation changed 971 evaluated
face vertices. `ematoblender-side-lip-probe.json`: the chosen side-lip bone
changed 320 evaluated face vertices. Both returned to the measured rest geometry.
The tongue and palate remained unchanged. Units are reported as native units;
the probes do not assume patient-calibrated physical dimensions.

`ematoblender-lip-probe.json` records a no-motion result for an X rotation of
the constrained upper-lip bone. It does not prove that every upper-lip control
is broken: its IK and rotation limits require the appropriate target/transform.
The probe correctly returned a nonzero exit status for that attempted operation.
Do not remove this result or describe every probe as passed.

## Reproduce the inspection

Acquire the small original release file at the publisher URL, retain it in a
research/cache directory outside the product, and verify its recorded identity.
Do not execute the old add-on or install its bundled scripts to inspect the data.
From the project root, with the original file at `/tmp/ematoblender-model.blend`:

```sh
npm run assets:inspect-rig -- --input /tmp/ematoblender-model.blend --report /tmp/rig-audit.json
npm run assets:probe-control -- --input /tmp/ematoblender-model.blend --report /tmp/jaw-probe.json --rig Armature --bone Jaw --angle 8
npm run assets:probe-control -- --input /tmp/ematoblender-model.blend --report /tmp/lip-probe.json --rig Armature --bone large-side-lip-left --angle 8
```

These are actual evaluated-geometry checks, not bone-count acceptance tests.
They show selected mechanical motion and return. They do not establish visual
quality, realistic soft-tissue mechanics, complete speech-organ coverage,
Arabic articulation, GLB pose fidelity or permission to adopt the asset.
