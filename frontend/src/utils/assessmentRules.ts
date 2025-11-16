import type { ProgressState } from "../api/types";
import type { TopicSnapshot } from "../types/assessment";

export function isSnapshotComplete(snapshot: TopicSnapshot | undefined): boolean {
  if (!snapshot) return false;
  if (snapshot.currentIsNa) {
    return snapshot.desiredIsNa;
  }
  return (
    typeof snapshot.currentMaturity === "number" &&
    (snapshot.desiredIsNa || typeof snapshot.desiredMaturity === "number")
  );
}

export function getProgressState(snapshot: TopicSnapshot | undefined): ProgressState {
  if (!snapshot) return "not_started";
  if (isSnapshotComplete(snapshot)) {
    return "complete";
  }
  const hasAnyValue =
    snapshot.currentIsNa ||
    snapshot.desiredIsNa ||
    snapshot.currentMaturity != null ||
    snapshot.desiredMaturity != null ||
    Boolean(snapshot.comment.trim()) ||
    snapshot.evidence.length > 0;
  return hasAnyValue ? "in_progress" : "not_started";
}

export function allowedDesiredLevels(
  snapshot: TopicSnapshot | undefined,
  ratingLevels: number[],
  treatNaAsZero: boolean,
): number[] {
  if (!snapshot) {
    return ratingLevels;
  }
  if (snapshot.currentIsNa) {
    return treatNaAsZero ? ratingLevels : [];
  }
  const minLevel = typeof snapshot.currentMaturity === "number" ? snapshot.currentMaturity : ratingLevels[0] ?? 0;
  return ratingLevels.filter((level) => level >= minLevel);
}

export function applyCurrentSelection(snapshot: TopicSnapshot, nextValue: number | null, isNa: boolean): TopicSnapshot {
  if (isNa) {
    return {
      ...snapshot,
      currentIsNa: true,
      currentMaturity: null,
      desiredIsNa: true,
      desiredMaturity: null,
    };
  }
  const current = nextValue ?? null;
  const shouldBumpDesired =
    snapshot.desiredIsNa ||
    snapshot.desiredMaturity == null ||
    (current != null && snapshot.desiredMaturity < current);
  return {
    ...snapshot,
    currentIsNa: false,
    currentMaturity: current,
    desiredIsNa: shouldBumpDesired ? false : snapshot.desiredIsNa,
    desiredMaturity: shouldBumpDesired ? current : snapshot.desiredMaturity,
  };
}

export function applyDesiredSelection(
  snapshot: TopicSnapshot,
  nextValue: number | null,
  isNa: boolean,
  ratingLevels: number[],
  treatNaAsZero: boolean,
): TopicSnapshot {
  if (isNa) {
    if (!snapshot.currentIsNa && !treatNaAsZero) {
      return snapshot;
    }
    return {
      ...snapshot,
      desiredIsNa: true,
      desiredMaturity: null,
    };
  }
  if (snapshot.currentIsNa && !treatNaAsZero) {
    return snapshot;
  }
  const floor = typeof snapshot.currentMaturity === "number" ? snapshot.currentMaturity : ratingLevels[0] ?? 1;
  const safeValue = nextValue != null ? Math.max(floor, nextValue) : floor;
  return {
    ...snapshot,
    desiredIsNa: false,
    desiredMaturity: safeValue,
  };
}

export interface ShortcutAction {
  target: "current" | "desired";
  value: number | null;
  isNa: boolean;
}

export function mapShortcut(key: string, shiftKey: boolean): ShortcutAction | null {
  const normalized = key.toLowerCase();
  if (normalized === "n") {
    return {
      target: shiftKey ? "desired" : "current",
      value: null,
      isNa: true,
    };
  }
  const numeric = Number(key);
  if (!Number.isNaN(numeric) && numeric >= 1 && numeric <= 5) {
    return {
      target: shiftKey ? "desired" : "current",
      value: numeric,
      isNa: false,
    };
  }
  return null;
}
