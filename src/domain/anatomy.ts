export type ReviewState = 'pending' | 'pass' | 'fail';

export interface StructureBinding {
  id: string;
  nodeIds: string[];
  regionId?: string;
  sourceKind: 'acquired' | 'authored' | 'mixed';
  licenseIds: string[];
}

export interface AnatomyManifest {
  schemaVersion: 1;
  assetVersion: string;
  glbSha256: string;
  units: 'm';
  coordinateFrame: { anterior: '+X'; superior: '+Y'; right: '+Z' };
  structures: StructureBinding[];
  clips: { name: string; durationSeconds: number }[];
  review: {
    geometry: ReviewState;
    visual: ReviewState;
    anatomyExpert: ReviewState;
    tajwidExpert: ReviewState;
  };
}

/** M2 inventory; a prior partial mouth study does not satisfy this gate. */
export const REQUIRED_STRUCTURE_IDS = [
  'head_skin', 'upper_lip', 'lower_lip', 'tongue', 'mouth_floor',
  'upper_teeth', 'lower_teeth', 'gingiva_upper', 'gingiva_lower',
  'hard_palate', 'soft_palate', 'uvula', 'nasal_cavity', 'pharynx',
  'laryngeal_context',
] as const;

/** Measured from the delivered file and the audited license registry. */
export interface AssetObservation {
  sha256: string;
  nodeIds: ReadonlySet<string>;
  regionIds: ReadonlySet<string>;
  clips: ReadonlyMap<string, number>;
  redistributableLicenseIds: ReadonlySet<string>;
}
