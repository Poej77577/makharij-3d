# MakeHuman asset-only snapshot

Repository: https://github.com/makehumancommunity/makehuman

Commit: `a8bc2d54ff0ac92e78ff71431b1023eda42bf482`.

`manifest.json` records unchanged acquired files and SHA-256 values. No nested
Git metadata or MakeHuman application logic is included. The accompanying
`LICENSE.CODE.md` is retained because the upstream overview references it;
it is the AGPL license of their program, not the CC0 license of these assets.

The header of `base.obj`, the eye OBJ/MHCLO/material and the selected target
files explicitly declares the September 2020 release as CC0. Upstream
`LICENSE.md`, section C, expressly includes the base mesh, targets, textures,
and MHCLO assets. The complete CC0 statement is `LICENSE.ASSETS.md`.

Original asset copyright notices name Data Collection AB, Joel Palmius and
Jonas Hauquier. Target files also retain their original Manuel Bastioni notice
and the stated transfer. These are authored character assets, not a measured
medical donor or proof of anatomical correctness.

## Units and frame

At this commit, `makehuman/apps/human.py`, `getHeightCm` (lines 694–699),
computes height in centimeters as ten times native mesh height. Thus one
native unit is 0.1 meter. For a head study we rotate the source +Z anterior
axis into canonical +X, retain +Y superior, and map source +X to canonical
-Z. This is a right-handed rotation and scale, not an anatomical registration
to the separate Badin research assembly.

## Eyes and masks

Eye OBJ coordinates are not already in the current base-mesh frame. The
original MHCLO file supplies three reference vertex IDs, barycentric weights,
offsets and per-axis scale references. Fit using those declarations against
the full original base-vertex array before any cropping or reindexing.
Format behavior was checked against upstream `makehuman/shared/proxy.py`,
`Proxy.getCoords` and `TMatrix.getMatrix`. Our asset adapter does not import
or distribute that application code.

Only the `body` face group is visible as skin. Named helper groups are fitting
cages and landmarks, not accepted anatomy. In particular `helper-tongue`
must not be called a finished anatomical tongue.

## Missing coverage

This snapshot does not provide a complete teaching nasal/pharyngeal/laryngeal
assembly, validated Arabic articulation, or acquired donor registration.
The original downloader's separate official asset repository returned
Repository not found during acquisition; no teeth/tongue from that unavailable
repository are claimed. Inspect this candidate before selecting or fitting it.
