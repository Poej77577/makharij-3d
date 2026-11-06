export type ArticulationPhase =
  | 'rest' | 'prepare' | 'approach' | 'articulate' | 'hold' | 'release' | 'return';
export type AirflowState = 'oral' | 'nasal' | 'both' | 'occluded' | 'not_visualized';

export interface PhaseInterval {
  phase: ArticulationPhase;
  startSeconds: number;
  endSeconds: number;
  airflow: AirflowState;
}

export interface ContactRequirement {
  kind: 'contact' | 'narrowing' | 'closure';
  activeRegionId: string;
  targetRegionId: string;
  startSeconds: number;
  endSeconds: number;
  calibrationRef: string;
}

export interface ArticulationDefinition {
  id: string;
  arabicLabel: string;
  groupId: string;
  clipName: string;
  calibrationAssetSha256: string;
  phases: PhaseInterval[];
  contacts: ContactRequirement[];
  sourceRefs: string[];
  availability: 'ready' | 'experimental' | 'not_implemented';
}

export interface PlaybackSnapshot {
  letterId: string;
  clipName: string;
  clipTimeSeconds: number;
  phase: ArticulationPhase;
  airflow: AirflowState;
  playing: boolean;
  speed: number;
}
