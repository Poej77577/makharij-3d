# Final independent tongue review

Exact baked GLB: `013445a15e559c3c34183dc64b92d6c8df55d7445d79f672f241fde2ec89efa5`.
Reviewed untextured native: `cb5ba1b7c0f9435d5b37266aabe6b635a5e734d6970c6dcea2e2978fb50a25b1`.
All 12 cached clay images match the final native review record; no older image was silently treated as final.

Retain this as the improved experimental working revision. The thinner free blade, descending root, removal of the duplicated anterior roof and lower gingival fins are visible progress. The normal interpolation and smoothing soften fine local ventral corrugation. The broad horseshoe-shaped ridge/recess beneath the anterior blade remains visible, especially ventrally/obliquely. It is not resolved into independently accepted anatomy. Root/floor insertions, posterior tissue context and Arabic articulation remain unaccepted.

The actual baked GLB passes the independent nonadjacent FCL tongue self-contact check at rest and the tip, dorsum and root endpoints, all at jaw=0. All four cases have zero nonadjacent intersecting triangle pairs, unsaturated enumeration, closed geometry, consistent winding and nondegenerate triangles. Counts range from 937,970 to 940,117 with a limit of 2,000,000. This does not test adjacent fold/strain or every combined/intermediate control, and does not establish anatomical realism.

Reproduce from the repository root:

```sh
.venv-qa/bin/python tools/qa/oral_tongue_self_contacts.py --expected-sha256 013445a15e559c3c34183dc64b92d6c8df55d7445d79f672f241fde2ec89efa5
```

The tool requires agreement among actual bytes, expected SHA and manifest SHA, and rechecks identity after export/testing. `identity-guard-self-test.json` confirms that a wrong expected hash and stale manifest are rejected. The existing reviewed FCL helper is reused with an explicit saturation guard.

Evidence: `self-contacts.json`, `visual-review.json`, `visual-input-identities.json`, `ventral-shape-comparison.png`, `baseline-to-final.png`, evaluated pose NPZ files and cached native images. Native visual endpoint pictures use jaw=.6; the independent isolated self cases use jaw=0. Tissue/dental contacts are owned by the separate contact review. Only the single authorized QA script was added; no model, builder, spec or viewer changed.
