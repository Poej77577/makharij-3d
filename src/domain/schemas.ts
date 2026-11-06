import { z } from 'zod';
import { REQUIRED_STRUCTURE_IDS, type AnatomyManifest, type AssetObservation } from './anatomy';
import type { ArticulationDefinition } from './articulation';

const id = z.string().trim().min(1);
const sha256 = z.string().regex(/^[a-f0-9]{64}$/, 'Expected a lowercase SHA-256');
const seconds = z.number().finite().nonnegative();
const review = z.enum(['pending', 'pass', 'fail']);
const unique = (values: string[]) => new Set(values).size === values.length;
const timeEpsilon = 1e-6; // serialization precision, not a physiological tolerance

export const anatomyManifestSchema: z.ZodType<AnatomyManifest> = z.object({
  schemaVersion: z.literal(1),
  assetVersion: id,
  glbSha256: sha256,
  units: z.literal('m'),
  coordinateFrame: z.object({ anterior: z.literal('+X'), superior: z.literal('+Y'), right: z.literal('+Z') }),
  structures: z.array(z.object({
    id,
    nodeIds: z.array(id).min(1).refine(unique, 'Duplicate node ID in structure'),
    regionId: id.optional(),
    sourceKind: z.enum(['acquired', 'authored', 'mixed']),
    licenseIds: z.array(id).min(1),
  })).min(1),
  clips: z.array(z.object({ name: id, durationSeconds: z.number().finite().positive() })),
  review: z.object({ geometry: review, visual: review, anatomyExpert: review, tajwidExpert: review }),
}).superRefine((manifest, context) => {
  if (!unique(manifest.structures.map(s => s.id))) context.addIssue({ code: 'custom', message: 'Duplicate anatomical structure ID' });
  if (!unique(manifest.clips.map(c => c.name))) context.addIssue({ code: 'custom', message: 'Duplicate clip name' });
});

export const articulationSchema: z.ZodType<ArticulationDefinition> = z.object({
  id, arabicLabel: id, groupId: id, clipName: id,
  calibrationAssetSha256: sha256,
  phases: z.array(z.object({
    phase: z.enum(['rest', 'prepare', 'approach', 'articulate', 'hold', 'release', 'return']),
    startSeconds: seconds, endSeconds: seconds,
    airflow: z.enum(['oral', 'nasal', 'both', 'occluded', 'not_visualized']),
  })).min(1),
  contacts: z.array(z.object({
    kind: z.enum(['contact', 'narrowing', 'closure']), activeRegionId: id, targetRegionId: id,
    startSeconds: seconds, endSeconds: seconds, calibrationRef: id,
  })),
  sourceRefs: z.array(id).min(1),
  availability: z.enum(['ready', 'experimental', 'not_implemented']),
}).superRefine((definition, context) => {
  let end = 0;
  for (const [index, phase] of definition.phases.entries()) {
    if (phase.endSeconds <= phase.startSeconds) context.addIssue({ code: 'custom', message: `Nonpositive phase interval ${index}` });
    if (Math.abs(phase.startSeconds - end) > timeEpsilon) context.addIssue({ code: 'custom', message: `Gap or overlap before phase ${index}` });
    end = phase.endSeconds;
  }
  for (const contact of definition.contacts) {
    if (contact.endSeconds <= contact.startSeconds || contact.endSeconds > end + timeEpsilon) context.addIssue({ code: 'custom', message: 'Contact interval outside the articulation timeline' });
  }
});

/** Fail closed on inventory, identity and rights; this is not anatomical approval. */
export function validateAssetContract(input: unknown, observed: AssetObservation): AnatomyManifest {
  const manifest = anatomyManifestSchema.parse(input);
  const problems: string[] = [];
  if (manifest.glbSha256 !== observed.sha256) problems.push('Delivered GLB checksum mismatch');
  const ids = new Set(manifest.structures.map(s => s.id));
  for (const required of REQUIRED_STRUCTURE_IDS) if (!ids.has(required)) problems.push(`Missing required structure: ${required}`);
  for (const structure of manifest.structures) {
    for (const node of structure.nodeIds) if (!observed.nodeIds.has(node)) problems.push(`Unknown node: ${node}`);
    if (structure.regionId && !observed.regionIds.has(structure.regionId)) problems.push(`Unknown region: ${structure.regionId}`);
    for (const license of structure.licenseIds) if (!observed.redistributableLicenseIds.has(license)) problems.push(`Redistribution not verified: ${license}`);
  }
  for (const clip of manifest.clips) {
    const duration = observed.clips.get(clip.name);
    if (duration === undefined || Math.abs(duration - clip.durationSeconds) > timeEpsilon) problems.push(`Missing or mismatched clip: ${clip.name}`);
  }
  if (problems.length) throw new Error(problems.join('\n'));
  return manifest;
}

export function validateArticulation(input: unknown, manifest: AnatomyManifest, regionIds: ReadonlySet<string>): ArticulationDefinition {
  const definition = articulationSchema.parse(input);
  if (definition.calibrationAssetSha256 !== manifest.glbSha256) throw new Error('Calibration belongs to another asset');
  const clip = manifest.clips.find(c => c.name === definition.clipName);
  if (!clip) throw new Error(`Unknown clip: ${definition.clipName}`);
  if (Math.abs(definition.phases.at(-1)!.endSeconds - clip.durationSeconds) > timeEpsilon) throw new Error('Timeline duration differs from the delivered clip');
  for (const contact of definition.contacts) {
    if (!regionIds.has(contact.activeRegionId) || !regionIds.has(contact.targetRegionId)) throw new Error('Unknown contact region');
  }
  return definition;
}
