export interface TopicSnapshot {
  currentMaturity: number | null;
  currentIsNa: boolean;
  desiredMaturity: number | null;
  desiredIsNa: boolean;
  comment: string;
  evidence: string[];
}

export type SnapshotMap = Record<number, TopicSnapshot>;
