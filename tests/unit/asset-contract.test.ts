import { describe, expect, it } from 'vitest';
import { REQUIRED_STRUCTURE_IDS, type AnatomyManifest, type AssetObservation } from '../../src/domain/anatomy';
import { anatomyManifestSchema, articulationSchema, validateArticulation, validateAssetContract } from '../../src/domain/schemas';

// Synthetic contract fixtures only. They are not a model or a review record.
const sha = 'a'.repeat(64);
function fixture(): { manifest: AnatomyManifest; observation: AssetObservation } {
  return {
    manifest: {
      schemaVersion: 1, assetVersion: 'contract-fixture', glbSha256: sha, units: 'm',
      coordinateFrame: { anterior: '+X', superior: '+Y', right: '+Z' },
      structures: REQUIRED_STRUCTURE_IDS.map(id => ({ id, nodeIds: ['continuous-mesh'], regionId: id, sourceKind: 'authored', licenseIds: ['fixture-license'] })),
      clips: [{ name: 'fixture-cycle', durationSeconds: 1 }],
      review: { geometry: 'pending', visual: 'pending', anatomyExpert: 'pending', tajwidExpert: 'pending' },
    },
    observation: { sha256: sha, nodeIds: new Set(['continuous-mesh']), regionIds: new Set(REQUIRED_STRUCTURE_IDS), clips: new Map([['fixture-cycle', 1]]), redistributableLicenseIds: new Set(['fixture-license']) },
  };
}
const articulation = () => ({ id: 'fixture', arabicLabel: 'اختبار', groupId: 'fixture', clipName: 'fixture-cycle', calibrationAssetSha256: sha, phases: [{ phase: 'rest', startSeconds: 0, endSeconds: .2, airflow: 'not_visualized' }, { phase: 'articulate', startSeconds: .2, endSeconds: 1, airflow: 'not_visualized' }], contacts: [{ kind: 'contact', activeRegionId: 'tongue', targetRegionId: 'hard_palate', startSeconds: .3, endSeconds: .5, calibrationRef: 'fixture-only' }], sourceRefs: ['fixture-not-a-source'], availability: 'experimental' });

describe('asset contract protects the anatomical gate', () => {
  it('supports different logical regions on one continuous mesh without granting review', () => {
    const { manifest, observation } = fixture();
    const checked = validateAssetContract(manifest, observation);
    expect(checked.review.anatomyExpert).toBe('pending');
    expect(checked.structures.filter(s => s.nodeIds[0] === 'continuous-mesh')).toHaveLength(REQUIRED_STRUCTURE_IDS.length);
  });
  it('rejects a partial mouth study with no external head', () => {
    const { manifest, observation } = fixture(); manifest.structures = manifest.structures.filter(s => s.id !== 'head_skin');
    expect(() => validateAssetContract(manifest, observation)).toThrow('Missing required structure: head_skin');
  });
  it('rejects a replaced GLB even when names still match', () => {
    const { manifest, observation } = fixture(); observation.sha256 = 'b'.repeat(64);
    expect(() => validateAssetContract(manifest, observation)).toThrow('checksum');
  });
  it('rejects unavailable semantic nodes', () => {
    const { manifest, observation } = fixture(); observation.nodeIds = new Set();
    expect(() => validateAssetContract(manifest, observation)).toThrow('Unknown node');
  });
  it('rejects lost region bindings after geometry changes', () => {
    const { manifest, observation } = fixture(); observation.regionIds = new Set();
    expect(() => validateAssetContract(manifest, observation)).toThrow('Unknown region');
  });
  it('rejects unresolved redistribution rights', () => {
    const { manifest, observation } = fixture(); observation.redistributableLicenseIds = new Set();
    expect(() => validateAssetContract(manifest, observation)).toThrow('Redistribution not verified');
  });
  it('rejects missing clips and altered clip durations', () => {
    const { manifest, observation } = fixture(); observation.clips = new Map();
    expect(() => validateAssetContract(manifest, observation)).toThrow('Missing or mismatched clip');
    observation.clips = new Map([['fixture-cycle', 2]]);
    expect(() => validateAssetContract(manifest, observation)).toThrow('Missing or mismatched clip');
  });
  it('rejects duplicate structure identities', () => {
    const { manifest } = fixture(); manifest.structures.push(manifest.structures[0]);
    expect(anatomyManifestSchema.safeParse(manifest).success).toBe(false);
  });
  it('rejects a wrong unit or axis declaration', () => {
    expect(anatomyManifestSchema.safeParse({ ...fixture().manifest, units: 'mm' }).success).toBe(false);
    expect(anatomyManifestSchema.safeParse({ ...fixture().manifest, coordinateFrame: { anterior: '-X', superior: '+Y', right: '+Z' } }).success).toBe(false);
  });
});

describe('articulation metadata follows the delivered asset', () => {
  it('accepts a contiguous timeline with real bindings', () => {
    const { manifest, observation } = fixture();
    expect(validateArticulation(articulation(), manifest, observation.regionIds).id).toBe('fixture');
  });
  it.each([.1, .3])('rejects a gap or overlap at %s seconds', start => {
    const value = articulation(); value.phases[1].startSeconds = start;
    expect(articulationSchema.safeParse(value).success).toBe(false);
  });
  it('rejects calibration for another exported model', () => {
    const value = articulation(); value.calibrationAssetSha256 = 'b'.repeat(64);
    expect(() => validateArticulation(value, fixture().manifest, new Set())).toThrow('another asset');
  });
  it('rejects a clip not present in the manifest', () => {
    const value = articulation(); value.clipName = 'missing';
    expect(() => validateArticulation(value, fixture().manifest, new Set())).toThrow('Unknown clip');
  });
  it('rejects contact beyond the timeline and zero-duration phases', () => {
    const value = articulation(); value.contacts[0].endSeconds = 2;
    expect(articulationSchema.safeParse(value).success).toBe(false);
    const other = articulation(); other.phases[0].endSeconds = 0;
    expect(articulationSchema.safeParse(other).success).toBe(false);
  });
  it('rejects an invented contact region', () => {
    const value = articulation(); value.contacts[0].targetRegionId = 'invented';
    expect(() => validateArticulation(value, fixture().manifest, fixture().observation.regionIds)).toThrow('Unknown contact region');
  });
});
